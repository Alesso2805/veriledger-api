from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from backend.app.application.dto.block import (
    BlockResponseDTO,
    FullBlockResponseDTO,
    MineBlockRequestDTO,
    PaginatedBlockResponseDTO,
    PaginatedFullBlockResponseDTO,
)
from backend.app.application.dto.transaction import TransactionResponseDTO
from backend.app.application.use_cases.ledger.mine_block import MineBlockUseCase
from backend.app.core.config import settings
from backend.app.domain.entities.block import Block
from backend.app.domain.entities.user import User, UserRole
from backend.app.domain.errors import BlockHeightTakenError
from backend.app.infrastructure.consensus.pow_service import ProofOfWorkServiceImpl
from backend.app.infrastructure.peers.httpx_peer_client import HttpxPeerClient
from backend.app.infrastructure.repositories.block_repository_impl import BlockRepositoryImpl
from backend.app.infrastructure.repositories.node_repository_impl import NodeRepositoryImpl
from backend.app.infrastructure.repositories.transaction_repository_impl import TransactionRepositoryImpl
from backend.app.infrastructure.security.sha256_hasher import SHA256HasherImpl
from backend.app.presentation.dependencies.auth import RequireRole
from backend.app.presentation.dependencies.database import DbSession
from backend.app.presentation.dependencies.limits import enforce_demo_mining_limit, one_mine_at_a_time

router = APIRouter(prefix="/blocks", tags=["blocks"])


def _stored_hash(block: Block) -> str:
    # A block read from the database always has its hash; only a block being mined has none
    assert block.block_hash is not None
    return block.block_hash


def _block_response(block: Block) -> BlockResponseDTO:
    return BlockResponseDTO(
        id=block.id,
        block_number=block.block_number,
        previous_hash=block.previous_hash,
        timestamp=block.timestamp,
        nonce=block.nonce,
        block_hash=_stored_hash(block),
        transaction_ids=block.transaction_ids,
        transaction_hashes=block.transaction_hashes,
    )


async def _full_block_response(block: Block, tx_repo: TransactionRepositoryImpl) -> FullBlockResponseDTO:
    transactions = await tx_repo.get_by_block_id(block.id)
    return FullBlockResponseDTO(
        id=block.id,
        block_number=block.block_number,
        previous_hash=block.previous_hash,
        timestamp=block.timestamp,
        nonce=block.nonce,
        block_hash=_stored_hash(block),
        transactions=[TransactionResponseDTO.from_entity(transaction, block) for transaction in transactions],
    )


@router.get("", response_model=PaginatedBlockResponseDTO)
async def get_blocks(
    db: DbSession,
    skip: int = Query(0, ge=0),
    # ADR-0006 caps the pages of public reads at 100
    limit: int = Query(100, ge=1, le=100),
) -> PaginatedBlockResponseDTO:
    block_repo = BlockRepositoryImpl(db)
    blocks = await block_repo.get_all_blocks(skip=skip, limit=limit)
    return PaginatedBlockResponseDTO(
        items=[_block_response(block) for block in blocks],
        total=await block_repo.count(),
        page=skip // limit + 1 if limit > 0 else 1,
        size=limit,
    )


@router.get("/full", response_model=PaginatedFullBlockResponseDTO)
async def get_blocks_full(
    db: DbSession,
    skip: int = Query(0, ge=0),
    # ADR-0006 caps the pages of public reads at 100
    limit: int = Query(100, ge=1, le=100),
) -> PaginatedFullBlockResponseDTO:
    block_repo = BlockRepositoryImpl(db)
    tx_repo = TransactionRepositoryImpl(db)
    blocks = await block_repo.get_all_blocks(skip=skip, limit=limit)
    return PaginatedFullBlockResponseDTO(
        items=[await _full_block_response(block, tx_repo) for block in blocks],
        total=await block_repo.count(),
        page=skip // limit + 1 if limit > 0 else 1,
        size=limit,
    )


# Declared after /full, so that "full" is not taken for a block hash
@router.get("/{block_hash}", response_model=FullBlockResponseDTO)
async def get_block(
    block_hash: str,
    db: DbSession,
) -> FullBlockResponseDTO:
    block = await BlockRepositoryImpl(db).get_by_hash(block_hash)
    if block is None:
        raise HTTPException(status_code=404, detail="Block not found")
    return await _full_block_response(block, TransactionRepositoryImpl(db))


@router.post("/mine", response_model=BlockResponseDTO)
async def mine_block(
    request: MineBlockRequestDTO,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: User = Depends(RequireRole([UserRole.TRADER, UserRole.ADMIN])),
) -> BlockResponseDTO:
    enforce_demo_mining_limit(current_user)

    block_repo = BlockRepositoryImpl(db)
    tx_repo = TransactionRepositoryImpl(db)
    node_repo = NodeRepositoryImpl(db)
    hasher = SHA256HasherImpl()
    consensus_service = ProofOfWorkServiceImpl(hasher)

    use_case = MineBlockUseCase(
        block_repo,
        tx_repo,
        consensus_service,
        hasher,
        node_repo,
        HttpxPeerClient(),
        difficulty=settings.mining_difficulty,
        reward=settings.mining_reward,
    )

    try:
        async with one_mine_at_a_time():
            block = await use_case.execute(miner_address=request.miner_address)
    except BlockHeightTakenError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Background tasks run after the response, so peers only hear of the block once it is committed
    background_tasks.add_task(use_case.broadcast_block)
    return block
