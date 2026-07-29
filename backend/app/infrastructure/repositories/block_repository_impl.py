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
        from sqlalchemy import delete
        from backend.app.infrastructure.models.transaction_model import TransactionModel
        from backend.app.domain.entities.transaction import TransactionStatus
        from dateutil.parser import isoparse
        
        # 1. Delete all blocks (this will set block_id to NULL for txs if no cascade, so we delete txs too)
        await self._session.execute(delete(TransactionModel).where(TransactionModel.status == TransactionStatus.CONFIRMED))
        await self._session.execute(delete(BlockModel))
        
        # 2. Re-insert the new chain
        # Note: We process them from oldest to newest if the list is newest first, wait. 
        # Usually list from /blocks is newest first (desc). So we just insert them as they are.
        for block_data in new_chain_data:
            block = BlockModel(
                id=block_data["id"],
                block_number=block_data["block_number"],
                previous_hash=block_data["previous_hash"],
                timestamp=isoparse(block_data["timestamp"]),
                nonce=block_data["nonce"],
                block_hash=block_data["block_hash"],
            )
            self._session.add(block)
            
            for tx_data in block_data.get("transactions", []):
                tx = TransactionModel(
                    id=tx_data["id"],
                    sender_address=tx_data["sender_address"],
                    receiver_address=tx_data["receiver_address"],
                    amount=tx_data["amount"],
                    fee=tx_data["fee"],
                    status=TransactionStatus(tx_data["status"]),
                    timestamp=isoparse(tx_data["timestamp"]),
                    signature=tx_data["signature"],
                    tx_hash=tx_data["tx_hash"],
                    block_id=block.id,
                )
                self._session.add(tx)
        
        await self._session.commit()

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
