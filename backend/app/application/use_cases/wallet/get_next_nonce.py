from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.signed_message import next_nonce


class GetNextNonceUseCase:
    def __init__(self, tx_repo: TransactionRepository):
        self.tx_repo = tx_repo

    async def execute(self, address: str) -> int:
        return next_nonce(await self.tx_repo.get_last_nonce(address))
