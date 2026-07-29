from abc import ABC, abstractmethod
from backend.app.domain.entities.block import Block


class ConsensusService(ABC):
    @abstractmethod
    def mine_block(self, block: Block, difficulty: int) -> tuple[int, str]:
        """
        Mines a block using Proof of Work.
        Returns:
            tuple[int, str]: A tuple containing the winning (nonce, block_hash)
        """
        pass
