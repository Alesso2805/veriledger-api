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

    @abstractmethod
    async def get_all_blocks(self, skip: int = 0, limit: int = 100) -> list[Block]:
        pass

    @abstractmethod
    async def replace_chain(self, new_chain_data: list[dict]) -> None:
        pass
