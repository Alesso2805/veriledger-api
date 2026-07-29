from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.dto.block import BlockResponseDTO
from backend.app.application.use_cases.ledger.mine_block import MineBlockUseCase
from backend.app.domain.entities.user import User
from backend.app.infrastructure.database import get_db_session
from backend.app.infrastructure.repositories.block_repository_impl import BlockRepositoryImpl
from backend.app.infrastructure.repositories.transaction_repository_impl import TransactionRepositoryImpl
from backend.app.infrastructure.security.sha256_hasher import SHA256HasherImpl
from backend.app.presentation.dependencies.auth import get_current_user

router = APIRouter(prefix="/blocks", tags=["blocks"])


@router.post("/mine", response_model=BlockResponseDTO)
async def mine_block(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> BlockResponseDTO:
    block_repo = BlockRepositoryImpl(db)
    tx_repo = TransactionRepositoryImpl(db)
    hasher = SHA256HasherImpl()

    use_case = MineBlockUseCase(block_repo, tx_repo, hasher)

    try:
        block = await use_case.execute()
        return BlockResponseDTO(
            id=block.id,
            block_number=block.block_number,
            previous_hash=block.previous_hash,
            timestamp=block.timestamp,
            block_hash=block.block_hash,
            transaction_ids=block.transaction_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
