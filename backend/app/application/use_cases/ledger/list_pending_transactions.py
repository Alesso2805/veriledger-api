from backend.app.application.dto.transaction import PaginatedTransactionResponseDTO, TransactionResponseDTO
from backend.app.domain.entities.transaction import TransactionStatus
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository


class ListPendingTransactionsUseCase:
    def __init__(self, tx_repo: TransactionRepository):
        self.tx_repo = tx_repo

    async def execute(self, skip: int, limit: int) -> PaginatedTransactionResponseDTO:
        transactions = await self.tx_repo.list_by_status(TransactionStatus.PENDING, skip, limit)
        return PaginatedTransactionResponseDTO(
            items=[TransactionResponseDTO.from_entity(transaction) for transaction in transactions],
            total=await self.tx_repo.count_by_status(TransactionStatus.PENDING),
            page=skip // limit + 1,
            size=limit,
        )
