import asyncio
import uuid
from datetime import UTC, datetime

import httpx

from backend.app.application.dto.transaction import TransactionCreateRequestDTO
from backend.app.domain.entities.node import Node
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.errors import NonceConflictError
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.services.hashing import HasherService
from backend.app.domain.ports.services.signature import SignatureService
from backend.app.domain.signed_message import build_signed_message, next_nonce


class SubmitTransactionUseCase:
    def __init__(
        self,
        tx_repo: TransactionRepository,
        hasher: HasherService,
        signature_service: SignatureService,
        node_repo: NodeRepository | None = None,
    ):
        self.tx_repo = tx_repo
        self.hasher = hasher
        self.signature_service = signature_service
        self.node_repo = node_repo
        self._peers: list[Node] = []

    async def execute(self, request: TransactionCreateRequestDTO) -> tuple[Transaction, bool]:
        """The transaction, and whether this request created it (False for a replay of a stored one)."""
        now = datetime.now(UTC)

        message = build_signed_message(
            sender_address=request.sender_address,
            receiver_address=request.receiver_address,
            amount=request.amount,
            fee=request.fee,
            nonce=request.nonce,
            payload=request.payload,
        )
        if not self.signature_service.verify_signature(request.sender_address, message, request.signature):
            raise ValueError("Invalid transaction signature")
        amount, fee = float(request.amount), float(request.fee)

        temp_tx = Transaction(
            id=str(uuid.uuid4()),
            sender_address=request.sender_address,
            receiver_address=request.receiver_address,
            amount=amount,
            fee=fee,
            status=TransactionStatus.PENDING,
            timestamp=now,
            signature=request.signature,
            payload=request.payload,
            nonce=request.nonce,
        )
        tx_hash = self.hasher.hash_transaction(temp_tx)

        # The hash covers what was signed, so a replayed body, or a peer echoing our broadcast, finds the
        # stored transaction before its nonce is judged as used
        existing_tx = await self.tx_repo.get_by_hash(tx_hash)
        if existing_tx:
            return existing_tx, False

        expected = next_nonce(await self.tx_repo.get_last_nonce(request.sender_address))
        if request.nonce != expected:
            raise NonceConflictError(
                f"Nonce {request.nonce} is not the next one for this sender; the next is {expected}"
            )

        balance = await self.tx_repo.get_balance(request.sender_address)
        total_required = amount + fee
        if balance < total_required:
            raise ValueError(f"Insufficient funds. Balance: {balance}, Required: {total_required}")

        temp_tx.tx_hash = tx_hash
        created_tx = await self.tx_repo.create(temp_tx)

        # Read the peers now: broadcast_transaction runs after the response, when this request's session is closed
        if self.node_repo:
            self._peers = await self.node_repo.get_all()

        return created_tx, True

    async def broadcast_transaction(self, request: TransactionCreateRequestDTO) -> None:
        nodes = self._peers
        if not nodes:
            return

        payload = request.model_dump()
        async with httpx.AsyncClient() as client:
            tasks = []
            for node in nodes:
                # Peers require a JWT this call does not send, so the broadcast fails between
                # authenticated nodes until VLA-19 adds a peer token
                tasks.append(client.post(f"{node.url}/transactions", json=payload))
            await asyncio.gather(*tasks, return_exceptions=True)
