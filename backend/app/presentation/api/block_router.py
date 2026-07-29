from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.dto.block import BlockResponseDTO
from backend.app.application.use_cases.ledger.mine_block import MineBlockUseCase
from backend.app.domain.entities.user import User
from backend.app.infrastructure.database import get_db_session
from backend.app.infrastructure.repositories.block_repository_impl import BlockRepositoryImpl
from backend.app.infrastructure.repositories.transaction_repository_impl import TransactionRepositoryImpl
from backend.app.infrastructure.repositories.node_repository_impl import NodeRepositoryImpl
from backend.app.infrastructure.security.sha256_hasher import SHA256HasherImpl
from backend.app.infrastructure.consensus.pow_service import ProofOfWorkServiceImpl
from backend.app.presentation.dependencies.auth import get_current_user

from backend.app.application.dto.block import BlockResponseDTO, PaginatedBlockResponseDTO, MineBlockRequestDTO

router = APIRouter(prefix="/blocks", tags=["blocks"])

@router.get("", response_model=PaginatedBlockResponseDTO)
async def get_blocks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PaginatedBlockResponseDTO:
    block_repo = BlockRepositoryImpl(db)
    blocks = await block_repo.get_all_blocks(skip=skip, limit=limit)
    
    items = [
        BlockResponseDTO(
            id=b.id,
            block_number=b.block_number,
            previous_hash=b.previous_hash,
            timestamp=b.timestamp,
            nonce=b.nonce,
            block_hash=b.block_hash,
            transaction_ids=b.transaction_ids,
        )
        for b in blocks
    ]
    
    return PaginatedBlockResponseDTO(
        items=items,
        total=len(items), # Simplified total for now
        page=skip // limit + 1 if limit > 0 else 1,
        size=limit
    )

from backend.app.application.dto.transaction import TransactionResponseDTO
from backend.app.application.dto.block import FullBlockResponseDTO, PaginatedFullBlockResponseDTO

@router.get("/full", response_model=PaginatedFullBlockResponseDTO)
async def get_blocks_full(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PaginatedFullBlockResponseDTO:
    block_repo = BlockRepositoryImpl(db)
    tx_repo = TransactionRepositoryImpl(db)
    
    blocks = await block_repo.get_all_blocks(skip=skip, limit=limit)
    items = []
    
    for b in blocks:
        txs = await tx_repo.get_by_block_id(b.id)
        tx_dtos = [
            TransactionResponseDTO(
                id=t.id,
                sender_address=t.sender_address,
                receiver_address=t.receiver_address,
                amount=t.amount,
                fee=t.fee,
                status=t.status,
                timestamp=t.timestamp,
                signature=t.signature,
                tx_hash=t.tx_hash,
                block_id=t.block_id,
            )
            for t in txs
        ]
        
        items.append(FullBlockResponseDTO(
            id=b.id,
            block_number=b.block_number,
            previous_hash=b.previous_hash,
            timestamp=b.timestamp,
            nonce=b.nonce,
            block_hash=b.block_hash,
            transactions=tx_dtos,
        ))
        
    return PaginatedFullBlockResponseDTO(
        items=items,
        total=len(items),
        page=skip // limit + 1 if limit > 0 else 1,
        size=limit
    )

@router.post("/mine", response_model=BlockResponseDTO)
async def mine_block(
    request: MineBlockRequestDTO,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> BlockResponseDTO:
    block_repo = BlockRepositoryImpl(db)
    tx_repo = TransactionRepositoryImpl(db)
    node_repo = NodeRepositoryImpl(db)
    hasher = SHA256HasherImpl()
    consensus_service = ProofOfWorkServiceImpl(hasher)

    use_case = MineBlockUseCase(block_repo, tx_repo, consensus_service, hasher, node_repo)

    try:
        block = await use_case.execute(miner_address=request.miner_address)
        return block
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
