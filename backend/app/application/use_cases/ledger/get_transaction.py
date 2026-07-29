from typing import Optional

from backend.app.domain.entities.transaction import Transaction
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository


class GetTransactionByHashUseCase:
    def __init__(self, tx_repo: TransactionRepository):
        self.tx_repo = tx_repo

    async def execute(self, tx_hash: str) -> Optional[Transaction]:
        return await self.tx_repo.get_by_hash(tx_hash)
