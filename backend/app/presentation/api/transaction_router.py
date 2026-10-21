from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from backend.app.application.dto.transaction import TransactionCreateRequestDTO, TransactionResponseDTO
from backend.app.application.use_cases.ledger.get_transaction import GetTransactionByHashUseCase
from backend.app.application.use_cases.ledger.submit_transaction import SubmitTransactionUseCase
from backend.app.domain.entities.user import User
from backend.app.infrastructure.repositories.node_repository_impl import NodeRepositoryImpl
from backend.app.infrastructure.repositories.transaction_repository_impl import TransactionRepositoryImpl
from backend.app.infrastructure.security.sha256_hasher import SHA256HasherImpl
from backend.app.infrastructure.security.ed25519_service import Ed25519ServiceImpl
from backend.app.presentation.dependencies.auth import get_current_user
from backend.app.presentation.dependencies.database import DbSession

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponseDTO, status_code=status.HTTP_201_CREATED)
async def submit_transaction(
    request: TransactionCreateRequestDTO,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> TransactionResponseDTO:
    tx_repo = TransactionRepositoryImpl(db)
    node_repo = NodeRepositoryImpl(db)
    hasher = SHA256HasherImpl()
    signature_service = Ed25519ServiceImpl()

    use_case = SubmitTransactionUseCase(tx_repo, hasher, signature_service, node_repo)

    try:
        transaction = await use_case.execute(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Background tasks run after the response, so peers only hear of the transaction once it is committed
    background_tasks.add_task(use_case.broadcast_transaction, request)

    return TransactionResponseDTO(
        id=transaction.id,
        sender_address=transaction.sender_address,
        receiver_address=transaction.receiver_address,
        amount=transaction.amount,
        fee=transaction.fee,
        status=transaction.status,
        timestamp=transaction.timestamp,
        signature=transaction.signature,
        tx_hash=transaction.tx_hash,
        payload=transaction.payload,
        block_id=transaction.block_id,
    )


@router.get("/{tx_hash}", response_model=TransactionResponseDTO)
async def get_transaction(
    tx_hash: str,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> TransactionResponseDTO:
    tx_repo = TransactionRepositoryImpl(db)
    use_case = GetTransactionByHashUseCase(tx_repo)

    transaction = await use_case.execute(tx_hash)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return TransactionResponseDTO(
        id=transaction.id,
        sender_address=transaction.sender_address,
        receiver_address=transaction.receiver_address,
        amount=transaction.amount,
        fee=transaction.fee,
        status=transaction.status,
        timestamp=transaction.timestamp,
        signature=transaction.signature,
        tx_hash=transaction.tx_hash,
        payload=transaction.payload,
        block_id=transaction.block_id,
    )
