import uuid
from datetime import UTC, datetime

from backend.app.application.dto.block import BlockResponseDTO
from backend.app.domain.chain_validator import COINBASE_SENDER, GENESIS_PREVIOUS_HASH
from backend.app.domain.entities.block import Block
from backend.app.domain.entities.node import Node
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.services.consensus import ConsensusService
from backend.app.domain.ports.services.hashing import HasherService
from backend.app.domain.ports.services.peer_client import PeerClient


class MineBlockUseCase:
    def __init__(
        self,
        block_repo: BlockRepository,
        tx_repo: TransactionRepository,
        consensus_service: ConsensusService,
        hasher: HasherService,
        node_repo: NodeRepository | None = None,
        peer_client: PeerClient | None = None,
        *,
        difficulty: int,
        reward: float,
    ):
        self.block_repo = block_repo
        self.tx_repo = tx_repo
        self.consensus_service = consensus_service
        self.hasher = hasher
        self.node_repo = node_repo
        self.peer_client = peer_client
        self.difficulty = difficulty
        self.reward = reward
        self._peers: list[Node] = []

    async def execute(self, miner_address: str) -> BlockResponseDTO:
        # The latest block before the mempool: a block committed in between then makes this one take its
        # height and fail with 409, instead of mining that block's transactions a second time
        latest_block = await self.block_repo.get_latest_block()
        pending_txs = await self.tx_repo.get_by_status(TransactionStatus.PENDING)

        total_fees = sum(tx.fee for tx in pending_txs)

        if latest_block:
            # A stored block always has its hash; only a block being mined has none
            assert latest_block.block_hash is not None
            previous_hash = latest_block.block_hash
            block_number = latest_block.block_number + 1
        else:
            previous_hash = GENESIS_PREVIOUS_HASH
            block_number = 0

        now = datetime.now(UTC)

        coinbase_tx = Transaction(
            id=str(uuid.uuid4()),
            sender_address=COINBASE_SENDER,
            receiver_address=miner_address,
            amount=self.reward + total_fees,
            fee=0.0,
            status=TransactionStatus.CONFIRMED,
            timestamp=now,
            signature="COINBASE",
            # The block number makes each coinbase's hash unique, since the hash covers no id or time
            nonce=block_number,
        )
        coinbase_tx.tx_hash = self.hasher.hash_transaction(coinbase_tx)

        all_txs_for_block = [coinbase_tx] + pending_txs
        tx_ids = [tx.id for tx in all_txs_for_block]

        block = Block(
            id=str(uuid.uuid4()),
            block_number=block_number,
            previous_hash=previous_hash,
            timestamp=now,
            transaction_ids=tx_ids,
        )

        nonce, block_hash = await self.consensus_service.mine_block(block, difficulty=self.difficulty)
        block.nonce = nonce
        block.block_hash = block_hash

        # Nothing is written until the nonce is found, and the block goes first: its unique height is where
        # a block mined at the same time stops this one, before the coinbase or any confirmation
        await self.block_repo.create(block)

        coinbase_tx.block_id = block.id
        await self.tx_repo.create(coinbase_tx)

        for tx in pending_txs:
            tx.status = TransactionStatus.CONFIRMED
            tx.block_id = block.id
            await self.tx_repo.update(tx)

        # Read the peers now: broadcast_block runs after the response, when this request's session is closed
        if self.node_repo:
            self._peers = await self.node_repo.get_all()

        return BlockResponseDTO(
            id=block.id,
            block_number=block.block_number,
            previous_hash=block.previous_hash,
            timestamp=block.timestamp,
            nonce=block.nonce,
            block_hash=block.block_hash,
            transaction_ids=block.transaction_ids,
            transaction_hashes=[tx.tx_hash for tx in all_txs_for_block if tx.tx_hash is not None],
        )

    async def broadcast_block(self) -> None:
        # Peers fetch our chain themselves: a new block only asks them to resolve
        if self._peers and self.peer_client:
            await self.peer_client.request_resolve([node.url for node in self._peers])
