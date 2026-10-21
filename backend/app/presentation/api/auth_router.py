from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.app.application.dto.user import LoginDTO, TokenDTO, UserResponseDTO
from backend.app.application.use_cases.auth.login import LoginUseCase
from backend.app.application.use_cases.auth.start_demo import StartDemoUseCase
from backend.app.core.config import settings
from backend.app.domain.entities.user import User
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from backend.app.infrastructure.security.jwt_service import JWTTokenService
from backend.app.infrastructure.security.password_hasher import PasswordHasherImpl
from backend.app.presentation.dependencies.auth import get_current_user
from backend.app.presentation.dependencies.database import DbSession
from backend.app.presentation.dependencies.limits import enforce_demo_account_limits

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenDTO)
async def login(db: DbSession, form_data: OAuth2PasswordRequestForm = Depends()) -> TokenDTO:
    user_repo = UserRepositoryImpl(db)
    password_hasher = PasswordHasherImpl()
    token_service = JWTTokenService()

    use_case = LoginUseCase(user_repo, password_hasher, token_service)

    try:
        login_dto = LoginDTO(email=form_data.username, password=form_data.password)
        token = await use_case.execute(login_dto)
        return token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/demo", response_model=TokenDTO, status_code=status.HTTP_201_CREATED)
async def start_demo(request: Request, db: DbSession) -> TokenDTO:
    # Only a demo deployment makes accounts for anyone who asks (ADR-0006)
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    await enforce_demo_account_limits(request, db)
    return await StartDemoUseCase(UserRepositoryImpl(db), JWTTokenService()).execute()


@router.get("/me", response_model=UserResponseDTO)
async def read_users_me(current_user: User = Depends(get_current_user)) -> UserResponseDTO:
    return UserResponseDTO.model_validate(current_user)
