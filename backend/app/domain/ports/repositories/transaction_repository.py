from abc import ABC, abstractmethod
from typing import Optional

from backend.app.domain.entities.transaction import Transaction, TransactionStatus


class TransactionRepository(ABC):
    @abstractmethod
    async def create(self, transaction: Transaction) -> Transaction:
        pass

    @abstractmethod
    async def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        pass

    @abstractmethod
    async def get_by_hash(self, tx_hash: str) -> Optional[Transaction]:
        pass

    @abstractmethod
    async def get_by_status(self, status: TransactionStatus) -> list[Transaction]:
        pass

    @abstractmethod
    async def update(self, transaction: Transaction) -> Transaction:
        pass
