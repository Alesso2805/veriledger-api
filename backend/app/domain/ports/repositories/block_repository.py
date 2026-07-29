from abc import ABC, abstractmethod
from typing import Optional

from backend.app.domain.entities.block import Block


class BlockRepository(ABC):
    @abstractmethod
    async def create(self, block: Block) -> Block:
        pass

    @abstractmethod
    async def get_latest_block(self) -> Optional[Block]:
        pass

    @abstractmethod
    async def get_by_hash(self, block_hash: str) -> Optional[Block]:
        pass
