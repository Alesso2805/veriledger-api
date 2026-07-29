import uuid
from datetime import datetime, timezone

from backend.app.application.dto.block import BlockResponseDTO
from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import TransactionStatus
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.services.consensus import ConsensusService


class MineBlockUseCase:
    def __init__(
        self,
        block_repo: BlockRepository,
        tx_repo: TransactionRepository,
        consensus_service: ConsensusService,
    ):
        self.block_repo = block_repo
        self.tx_repo = tx_repo
        self.consensus_service = consensus_service

    async def execute(self) -> BlockResponseDTO:
        # Get pending transactions
        pending_txs = await self.tx_repo.get_by_status(TransactionStatus.PENDING)
        tx_ids = [tx.id for tx in pending_txs]

        # Get latest block to find previous hash
        latest_block = await self.block_repo.get_latest_block()
        if latest_block:
            previous_hash = latest_block.block_hash
            block_number = latest_block.block_number + 1
        else:
            # Genesis block
            previous_hash = "0" * 64
            block_number = 0

        now = datetime.now(timezone.utc)

        block = Block(
            id=str(uuid.uuid4()),
            block_number=block_number,
            previous_hash=previous_hash,
            timestamp=now,
            transaction_ids=tx_ids,
        )

        # Mine the block (find nonce and hash)
        # We use a difficulty of 4 for testing purposes
        nonce, block_hash = self.consensus_service.mine_block(block, difficulty=4)
        block.nonce = nonce
        block.block_hash = block_hash

        # Save the block
        await self.block_repo.create(block)

        # Update transactions to CONFIRMED and link to this block
        for tx in pending_txs:
            tx.status = TransactionStatus.CONFIRMED
            tx.block_id = block.id
            await self.tx_repo.update(tx)

        return BlockResponseDTO(
            id=block.id,
            block_number=block.block_number,
            previous_hash=block.previous_hash,
            timestamp=block.timestamp,
            nonce=block.nonce,
            block_hash=block.block_hash,
            transaction_ids=block.transaction_ids,
        )
