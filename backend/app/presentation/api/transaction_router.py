from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status

from backend.app.application.dto.transaction import (
    PaginatedTransactionResponseDTO,
    TransactionCreateRequestDTO,
    TransactionResponseDTO,
)
from backend.app.application.use_cases.ledger.get_transaction import GetTransactionByHashUseCase
from backend.app.application.use_cases.ledger.list_pending_transactions import ListPendingTransactionsUseCase
from backend.app.application.use_cases.ledger.submit_transaction import SubmitTransactionUseCase
from backend.app.domain.entities.user import User, UserRole
from backend.app.domain.errors import NonceConflictError
from backend.app.infrastructure.peers.httpx_peer_client import HttpxPeerClient
from backend.app.infrastructure.repositories.block_repository_impl import BlockRepositoryImpl
from backend.app.infrastructure.repositories.node_repository_impl import NodeRepositoryImpl
from backend.app.infrastructure.repositories.transaction_repository_impl import TransactionRepositoryImpl
from backend.app.infrastructure.security.ed25519_service import Ed25519ServiceImpl
from backend.app.infrastructure.security.sha256_hasher import SHA256HasherImpl
from backend.app.presentation.dependencies.auth import RequireRoleOrPeer
from backend.app.presentation.dependencies.database import DbSession
from backend.app.presentation.dependencies.limits import enforce_transaction_limit

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponseDTO, status_code=status.HTTP_201_CREATED)
async def submit_transaction(
    request: TransactionCreateRequestDTO,
    background_tasks: BackgroundTasks,
    response: Response,
    db: DbSession,
    # A peer offers the transactions it received; the signature, balance and nonce are checked all the same
    current_user: User | None = Depends(RequireRoleOrPeer(list(UserRole))),
) -> TransactionResponseDTO:
    # A peer relays what its own node already limited
    if current_user is not None:
        enforce_transaction_limit(request.sender_address)

    tx_repo = TransactionRepositoryImpl(db)
    node_repo = NodeRepositoryImpl(db)
    hasher = SHA256HasherImpl()
    signature_service = Ed25519ServiceImpl()

    use_case = SubmitTransactionUseCase(tx_repo, hasher, signature_service, node_repo, HttpxPeerClient())

    try:
        transaction, created = await use_case.execute(request)
    except NonceConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if created:
        # Background tasks run after the response, so peers only hear of the transaction once it is committed
        background_tasks.add_task(use_case.broadcast_transaction, request)
    else:
        # A replay of a stored transaction: nothing was created, and peers already have it
        response.status_code = status.HTTP_200_OK

    return TransactionResponseDTO.from_entity(transaction)


@router.get("", response_model=PaginatedTransactionResponseDTO)
async def list_transactions(
    db: DbSession,
    # Only the mempool for now: a confirmed transaction would also need its block, which this list does not read
    tx_status: Literal["PENDING"] = Query("PENDING", alias="status"),
    skip: int = Query(0, ge=0),
    # ADR-0006 caps the pages of public reads at 100
    limit: int = Query(100, ge=1, le=100),
) -> PaginatedTransactionResponseDTO:
    return await ListPendingTransactionsUseCase(TransactionRepositoryImpl(db)).execute(skip=skip, limit=limit)


@router.get("/{tx_hash}", response_model=TransactionResponseDTO)
async def get_transaction(
    tx_hash: str,
    db: DbSession,
) -> TransactionResponseDTO:
    use_case = GetTransactionByHashUseCase(TransactionRepositoryImpl(db), BlockRepositoryImpl(db))

    transaction = await use_case.execute(tx_hash)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction
