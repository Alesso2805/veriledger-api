from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.infrastructure.models.transaction_model import TransactionModel


class TransactionRepositoryImpl(TransactionRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, transaction: Transaction) -> Transaction:
        model = TransactionModel(
            id=transaction.id,
            sender_address=transaction.sender_address,
            receiver_address=transaction.receiver_address,
            amount=transaction.amount,
            status=transaction.status,
            timestamp=transaction.timestamp,
            tx_hash=transaction.tx_hash,
            block_id=transaction.block_id,
        )
        self._session.add(model)
        await self._session.commit()
        return transaction

    async def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        stmt = select(TransactionModel).where(TransactionModel.id == transaction_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def get_by_hash(self, tx_hash: str) -> Optional[Transaction]:
        stmt = select(TransactionModel).where(TransactionModel.tx_hash == tx_hash)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def get_by_status(self, status: TransactionStatus) -> list[Transaction]:
        stmt = select(TransactionModel).where(TransactionModel.status == status)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def update(self, transaction: Transaction) -> Transaction:
        stmt = select(TransactionModel).where(TransactionModel.id == transaction.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.status = transaction.status
            model.tx_hash = transaction.tx_hash
            model.block_id = transaction.block_id
            await self._session.commit()
        return transaction

    def _model_to_entity(self, model: TransactionModel) -> Transaction:
        return Transaction(
            id=model.id,
            sender_address=model.sender_address,
            receiver_address=model.receiver_address,
            amount=float(model.amount),
            status=model.status,
            timestamp=model.timestamp,
            tx_hash=model.tx_hash,
            block_id=model.block_id,
        )
