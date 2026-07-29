from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.dto.user import UserCreateDTO, UserResponseDTO
from backend.app.application.use_cases.auth.register_user import RegisterUserUseCase
from backend.app.domain.entities.user import User, UserRole
from backend.app.infrastructure.database import get_db_session
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from backend.app.infrastructure.security.password_hasher import PasswordHasherImpl
from backend.app.presentation.dependencies.auth import RequireRole

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreateDTO,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(RequireRole([UserRole.ADMIN])),
) -> UserResponseDTO:
    user_repo = UserRepositoryImpl(db)
    password_hasher = PasswordHasherImpl()

    use_case = RegisterUserUseCase(user_repo, password_hasher)

    try:
        user = await use_case.execute(data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
