from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository


class GetBalanceUseCase:
    def __init__(self, tx_repo: TransactionRepository):
        self.tx_repo = tx_repo

    async def execute(self, address: str) -> float:
        return await self.tx_repo.get_balance(address)
