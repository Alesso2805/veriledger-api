from backend.app.application.dto.transaction import PaginatedTransactionResponseDTO, TransactionResponseDTO
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository


class ListAddressTransactionsUseCase:
    def __init__(self, tx_repo: TransactionRepository, block_repo: BlockRepository):
        self.tx_repo = tx_repo
        self.block_repo = block_repo

    async def execute(self, address: str, skip: int, limit: int) -> PaginatedTransactionResponseDTO:
        transactions = await self.tx_repo.list_by_address(address, skip, limit)
        # The page's blocks in one query, not one per confirmed transaction
        block_ids = sorted({tx.block_id for tx in transactions if tx.block_id})
        blocks = {block.id: block for block in await self.block_repo.get_by_ids(block_ids)} if block_ids else {}
        return PaginatedTransactionResponseDTO(
            items=[
                TransactionResponseDTO.from_entity(tx, blocks.get(tx.block_id) if tx.block_id else None)
                for tx in transactions
            ],
            total=await self.tx_repo.count_by_address(address),
            page=skip // limit + 1,
            size=limit,
        )
