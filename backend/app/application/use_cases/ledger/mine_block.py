import asyncio
import httpx
import uuid
from datetime import datetime, timezone

from backend.app.application.dto.block import BlockResponseDTO
from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import TransactionStatus, Transaction
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.services.consensus import ConsensusService
from backend.app.domain.ports.services.hashing import HasherService


class MineBlockUseCase:
    def __init__(
        self,
        block_repo: BlockRepository,
        tx_repo: TransactionRepository,
        consensus_service: ConsensusService,
        hasher: HasherService,
        node_repo: NodeRepository = None,
    ):
        self.block_repo = block_repo
        self.tx_repo = tx_repo
        self.consensus_service = consensus_service
        self.hasher = hasher
        self.node_repo = node_repo

    async def execute(self, miner_address: str) -> BlockResponseDTO:
        # Get pending transactions
        pending_txs = await self.tx_repo.get_by_status(TransactionStatus.PENDING)
        
        # Calculate total fees from pending txs
        total_fees = sum(tx.fee for tx in pending_txs)
        
        now = datetime.now(timezone.utc)
        
        # Create Coinbase transaction
        coinbase_tx = Transaction(
            id=str(uuid.uuid4()),
            sender_address="SYSTEM",
            receiver_address=miner_address,
            amount=50.0 + total_fees,
            fee=0.0,
            status=TransactionStatus.CONFIRMED,
            timestamp=now,
            signature="COINBASE",
        )
        coinbase_tx.tx_hash = self.hasher.hash_transaction(coinbase_tx)
        
        # Save coinbase tx
        await self.tx_repo.create(coinbase_tx)
        
        all_txs_for_block = [coinbase_tx] + pending_txs
        tx_ids = [tx.id for tx in all_txs_for_block]

        # Get latest block to find previous hash
        latest_block = await self.block_repo.get_latest_block()
        if latest_block:
            previous_hash = latest_block.block_hash
            block_number = latest_block.block_number + 1
        else:
            # Genesis block
            previous_hash = "0" * 64
            block_number = 0

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
        
        # Update coinbase block_id
        coinbase_tx.block_id = block.id
        await self.tx_repo.update(coinbase_tx)

        # Update pending transactions to CONFIRMED and link to this block
        for tx in pending_txs:
            tx.status = TransactionStatus.CONFIRMED
            tx.block_id = block.id
            await self.tx_repo.update(tx)

        # Broadcast resolve signal
        if self.node_repo:
            asyncio.create_task(self._broadcast_block())

        return BlockResponseDTO(
            id=block.id,
            block_number=block.block_number,
            previous_hash=block.previous_hash,
            timestamp=block.timestamp,
            nonce=block.nonce,
            block_hash=block.block_hash,
            transaction_ids=block.transaction_ids,
        )

    async def _broadcast_block(self):
        nodes = await self.node_repo.get_all()
        if not nodes:
            return
            
        async with httpx.AsyncClient() as client:
            tasks = []
            for node in nodes:
                # Trigger peers to resolve conflicts with our new chain
                tasks.append(client.post(f"{node.url}/nodes/resolve"))
            await asyncio.gather(*tasks, return_exceptions=True)
