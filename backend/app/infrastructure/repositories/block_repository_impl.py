from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.domain.entities.block import Block
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.infrastructure.models.block_model import BlockModel


class BlockRepositoryImpl(BlockRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, block: Block) -> Block:
        model = BlockModel(
            id=block.id,
            block_number=block.block_number,
            previous_hash=block.previous_hash,
            timestamp=block.timestamp,
            nonce=block.nonce,
            block_hash=block.block_hash,
        )
        self._session.add(model)
        await self._session.commit()
        return block

    async def get_latest_block(self) -> Optional[Block]:
        stmt = (
            select(BlockModel)
            .order_by(desc(BlockModel.block_number))
            .limit(1)
            .options(selectinload(BlockModel.transactions))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def get_by_hash(self, block_hash: str) -> Optional[Block]:
        stmt = (
            select(BlockModel)
            .where(BlockModel.block_hash == block_hash)
            .options(selectinload(BlockModel.transactions))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def get_all_blocks(self, skip: int = 0, limit: int = 100) -> list[Block]:
        stmt = (
            select(BlockModel)
            .order_by(desc(BlockModel.block_number))
            .offset(skip)
            .limit(limit)
            .options(selectinload(BlockModel.transactions))
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def replace_chain(self, new_chain_data: list[dict]) -> None:
        pass

    def _model_to_entity(self, model: BlockModel) -> Block:
        tx_ids = [tx.id for tx in model.transactions] if hasattr(model, "transactions") else []
        return Block(
            id=model.id,
            block_number=model.block_number,
            previous_hash=model.previous_hash,
            timestamp=model.timestamp,
            nonce=model.nonce,
            block_hash=model.block_hash,
            transaction_ids=tx_ids,
        )
