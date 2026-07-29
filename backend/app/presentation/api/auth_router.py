from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.dto.user import LoginDTO, TokenDTO, UserResponseDTO
from backend.app.application.use_cases.auth.login import LoginUseCase
from backend.app.domain.entities.user import User
from backend.app.infrastructure.database import get_db_session
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from backend.app.infrastructure.security.jwt_service import JWTTokenService
from backend.app.infrastructure.security.password_hasher import PasswordHasherImpl
from backend.app.presentation.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenDTO)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db_session)
) -> TokenDTO:
    user_repo = UserRepositoryImpl(db)
    password_hasher = PasswordHasherImpl()
    token_service = JWTTokenService()

    use_case = LoginUseCase(user_repo, password_hasher, token_service)

    try:
        login_dto = LoginDTO(email=form_data.username, password=form_data.password)  # type: ignore
        token = await use_case.execute(login_dto)
        return token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.get("/me", response_model=UserResponseDTO)
async def read_users_me(current_user: User = Depends(get_current_user)) -> UserResponseDTO:
    return UserResponseDTO.model_validate(current_user)
