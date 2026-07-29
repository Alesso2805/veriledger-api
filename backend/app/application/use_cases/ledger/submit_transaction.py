import uuid
from datetime import datetime, timezone

from backend.app.application.dto.transaction import TransactionCreateRequestDTO
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.services.hashing import HasherService


class SubmitTransactionUseCase:
    def __init__(self, tx_repo: TransactionRepository, hasher: HasherService):
        self.tx_repo = tx_repo
        self.hasher = hasher

    async def execute(self, request: TransactionCreateRequestDTO) -> Transaction:
        now = datetime.now(timezone.utc)
        
        transaction = Transaction(
            id=str(uuid.uuid4()),
            sender_address=request.sender_address,
            receiver_address=request.receiver_address,
            amount=request.amount,
            status=TransactionStatus.PENDING,
            timestamp=now,
        )

        # Hash it immediately to seal its contents
        tx_hash = self.hasher.hash_transaction(transaction)
        transaction.tx_hash = tx_hash

        return await self.tx_repo.create(transaction)
