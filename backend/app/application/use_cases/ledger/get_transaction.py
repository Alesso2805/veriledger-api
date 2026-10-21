from backend.app.application.dto.transaction import TransactionResponseDTO
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository


class GetTransactionByHashUseCase:
    def __init__(self, tx_repo: TransactionRepository, block_repo: BlockRepository):
        self.tx_repo = tx_repo
        self.block_repo = block_repo

    async def execute(self, tx_hash: str) -> TransactionResponseDTO | None:
        transaction = await self.tx_repo.get_by_hash(tx_hash)
        if transaction is None:
            return None
        block = await self.block_repo.get_by_id(transaction.block_id) if transaction.block_id else None
        return TransactionResponseDTO.from_entity(transaction, block)
