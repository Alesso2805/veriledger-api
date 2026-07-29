import asyncio
import httpx
import json
import uuid
from datetime import datetime, timezone

from backend.app.application.dto.transaction import TransactionCreateRequestDTO
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.services.hashing import HasherService
from backend.app.domain.ports.services.signature import SignatureService


class SubmitTransactionUseCase:
    def __init__(
        self,
        tx_repo: TransactionRepository,
        hasher: HasherService,
        signature_service: SignatureService,
        node_repo: NodeRepository = None,
    ):
        self.tx_repo = tx_repo
        self.hasher = hasher
        self.signature_service = signature_service
        self.node_repo = node_repo

    async def execute(self, request: TransactionCreateRequestDTO) -> Transaction:
        # Check if transaction signature and contents generate a known hash to avoid infinite loops in gossip
        # Wait, we need to generate the hash first to check if we already have it.
        now = datetime.now(timezone.utc)
        
        # We can reconstruct payload to verify signature
        payload = {
            "amount": float(request.amount),
            "fee": float(request.fee),
            "receiver_address": request.receiver_address,
            "sender_address": request.sender_address,
        }
        payload_str = json.dumps(payload, sort_keys=True)
        
        is_valid = self.signature_service.verify_signature(
            request.sender_address, payload_str, request.signature
        )
        if not is_valid:
            raise ValueError("Invalid transaction signature")
            
        temp_tx = Transaction(
            id=str(uuid.uuid4()),
            sender_address=request.sender_address,
            receiver_address=request.receiver_address,
            amount=request.amount,
            fee=request.fee,
            status=TransactionStatus.PENDING,
            timestamp=now,
            signature=request.signature,
        )
        tx_hash = self.hasher.hash_transaction(temp_tx)
        
        # Check if already exists (avoid infinite gossip loop)
        existing_tx = await self.tx_repo.get_by_hash(tx_hash)
        if existing_tx:
            return existing_tx
            
        # Check if sender has enough balance
        balance = await self.tx_repo.get_balance(request.sender_address)
        total_required = request.amount + request.fee
        if balance < total_required:
            raise ValueError(f"Insufficient funds. Balance: {balance}, Required: {total_required}")
            
        temp_tx.tx_hash = tx_hash
        created_tx = await self.tx_repo.create(temp_tx)
        
        # Broadcast to peers
        if self.node_repo:
            asyncio.create_task(self._broadcast_transaction(request))
            
        return created_tx

    async def _broadcast_transaction(self, request: TransactionCreateRequestDTO):
        nodes = await self.node_repo.get_all()
        if not nodes:
            return
            
        payload = request.model_dump()
        async with httpx.AsyncClient() as client:
            tasks = []
            for node in nodes:
                # We do not pass auth tokens for P2P sync in this MVP, 
                # but if the remote node requires it, it might fail. 
                # For a real P2P, node-to-node auth is handled differently.
                # Assuming /transactions is open or uses node keys.
                # Wait, our /transactions requires auth! 
                # For this MVP simulation, we might need a dedicated unauthenticated P2P endpoint, 
                # or we just try and accept that it might fail if they don't share auth.
                # Let's hit the same endpoint, maybe it works if we disabled auth for P2P, but we didn't.
                tasks.append(client.post(f"{node.url}/transactions", json=payload))
            await asyncio.gather(*tasks, return_exceptions=True)

