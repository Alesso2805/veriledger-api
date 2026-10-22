from abc import ABC, abstractmethod
from typing import NamedTuple

from backend.app.domain.entities.block import Block


class MinedBlock(NamedTuple):
    nonce: int
    block_hash: str


class ConsensusService(ABC):
    @abstractmethod
    async def mine_block(self, block: Block, difficulty: int) -> MinedBlock:
        """Proof of Work, without blocking the event loop."""
