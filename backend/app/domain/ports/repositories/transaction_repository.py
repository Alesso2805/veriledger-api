from abc import ABC, abstractmethod

from backend.app.domain.entities.transaction import Transaction, TransactionStatus


class TransactionRepository(ABC):
    @abstractmethod
    async def create(self, transaction: Transaction) -> Transaction:
        pass

    @abstractmethod
    async def get_by_id(self, transaction_id: str) -> Transaction | None:
        pass

    @abstractmethod
    async def get_by_hash(self, tx_hash: str) -> Transaction | None:
        pass

    @abstractmethod
    async def get_by_status(self, status: TransactionStatus) -> list[Transaction]:
        pass

    @abstractmethod
    async def list_by_status(self, status: TransactionStatus, skip: int, limit: int) -> list[Transaction]:
        pass

    @abstractmethod
    async def count_by_status(self, status: TransactionStatus) -> int:
        pass

    @abstractmethod
    async def get_by_block_id(self, block_id: str) -> list[Transaction]:
        pass

    @abstractmethod
    async def update(self, transaction: Transaction) -> Transaction:
        pass

    @abstractmethod
    async def get_last_nonce(self, address: str) -> int | None:
        pass

    @abstractmethod
    async def get_balance(self, address: str) -> float:
        pass
