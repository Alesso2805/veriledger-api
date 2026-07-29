import json
import uuid
from datetime import datetime, timezone

from backend.app.application.dto.transaction import TransactionCreateRequestDTO
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.services.hashing import HasherService
from backend.app.domain.ports.services.signature import SignatureService


class SubmitTransactionUseCase:
    def __init__(
        self,
        tx_repo: TransactionRepository,
        hasher: HasherService,
        signature_service: SignatureService,
    ):
        self.tx_repo = tx_repo
        self.hasher = hasher
        self.signature_service = signature_service

    async def execute(self, request: TransactionCreateRequestDTO) -> Transaction:
        # Check if sender has enough balance
        balance = await self.tx_repo.get_balance(request.sender_address)
        total_required = request.amount + request.fee
        if balance < total_required:
            raise ValueError(f"Insufficient funds. Balance: {balance}, Required: {total_required}")

        # Reconstruct the deterministic payload that the user signed
        payload = {
            "amount": float(request.amount),
            "fee": float(request.fee),
            "receiver_address": request.receiver_address,
            "sender_address": request.sender_address,
        }
        payload_str = json.dumps(payload, sort_keys=True)

        # Verify signature
        is_valid = self.signature_service.verify_signature(
            request.sender_address, payload_str, request.signature
        )
        if not is_valid:
            raise ValueError("Invalid transaction signature")

        now = datetime.now(timezone.utc)

        transaction = Transaction(
            id=str(uuid.uuid4()),
            sender_address=request.sender_address,
            receiver_address=request.receiver_address,
            amount=request.amount,
            fee=request.fee,
            status=TransactionStatus.PENDING,
            timestamp=now,
            signature=request.signature,
        )

        # Hash it immediately to seal its contents
        tx_hash = self.hasher.hash_transaction(transaction)
        transaction.tx_hash = tx_hash

        return await self.tx_repo.create(transaction)
