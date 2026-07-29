import uuid
from datetime import datetime, timezone

from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import TransactionStatus
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.services.hashing import HasherService


class MineBlockUseCase:
    def __init__(
        self,
        block_repo: BlockRepository,
        tx_repo: TransactionRepository,
        hasher: HasherService,
    ):
        self.block_repo = block_repo
        self.tx_repo = tx_repo
        self.hasher = hasher

    async def execute(self) -> Block:
        # Get all pending transactions
        pending_txs = await self.tx_repo.get_by_status(TransactionStatus.PENDING)
        
        if not pending_txs:
            raise ValueError("No pending transactions to mine.")

        latest_block = await self.block_repo.get_latest_block()
        next_block_number = latest_block.block_number + 1 if latest_block else 0
        
        # In a real blockchain, genesis block is hardcoded, but here we can just use a dummy hash if none
        previous_hash = latest_block.block_hash if latest_block else "0" * 64

        now = datetime.now(timezone.utc)
        block = Block(
            id=str(uuid.uuid4()),
            block_number=next_block_number,
            previous_hash=previous_hash,
            timestamp=now,
            transaction_ids=[tx.id for tx in pending_txs]
        )

        block_hash = self.hasher.hash_block(block)
        block.block_hash = block_hash

        # Save block
        await self.block_repo.create(block)

        # Update all transactions to CONFIRMED and link to block
        for tx in pending_txs:
            tx.status = TransactionStatus.CONFIRMED
            tx.block_id = block.id
            await self.tx_repo.update(tx)

        return block
