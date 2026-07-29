from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.entities.user import User, UserRole
from backend.app.infrastructure.database import get_db_session
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from backend.app.infrastructure.security.jwt_service import JWTTokenService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_token_service() -> JWTTokenService:
    return JWTTokenService()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
    token_service: JWTTokenService = Depends(get_token_service),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = token_service.verify_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except ValueError as e:
        raise credentials_exception from e

    user_repo = UserRepositoryImpl(db)
    user = await user_repo.get_by_id(str(user_id))
    if user is None:
        raise credentials_exception

    return user


class RequireRole:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return user
