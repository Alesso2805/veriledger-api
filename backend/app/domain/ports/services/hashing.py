from abc import ABC, abstractmethod

from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import Transaction


class HasherService(ABC):
    @abstractmethod
    def hash_transaction(self, transaction: Transaction) -> str:
        pass

    @abstractmethod
    def hash_block(self, block: Block) -> str:
        pass
