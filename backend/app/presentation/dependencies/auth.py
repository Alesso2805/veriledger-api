import hmac
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.domain.entities.user import User, UserRole
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from backend.app.infrastructure.security.jwt_service import JWTTokenService
from backend.app.presentation.dependencies.database import DbSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# The same scheme without its own 401, for the routes a peer node may call instead of a user
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
peer_token_header = APIKeyHeader(name="X-Peer-Token", auto_error=False)


def get_token_service() -> JWTTokenService:
    return JWTTokenService()


async def get_current_user(
    db: DbSession,
    token: str = Depends(oauth2_scheme),
    token_service: JWTTokenService = Depends(get_token_service),
) -> User:
    return await user_from_token(db, token, token_service)


async def user_from_token(db: AsyncSession, token: str, token_service: JWTTokenService) -> User:
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
    # A demo token ends with its account, but the account's own date is the rule
    if user.is_expired(datetime.now(UTC)):
        raise credentials_exception

    return user


def is_peer(token: str | None = Depends(peer_token_header)) -> bool:
    expected = settings.peer_token
    if not expected or token is None:
        return False
    # Constant time, so the answer's timing does not tell how much of a guess was right
    return hmac.compare_digest(token.encode(), expected.encode())


def require_role(user: User, allowed_roles: list[UserRole]) -> User:
    if user.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user


class RequireRole:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        return require_role(user, self.allowed_roles)


class RequireRoleOrPeer:
    """RequireRole, or another node of the network presenting PEER_TOKEN, which has no user (None)."""

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        db: DbSession,
        peer: bool = Depends(is_peer),
        token: str | None = Depends(optional_oauth2_scheme),
        token_service: JWTTokenService = Depends(get_token_service),
    ) -> User | None:
        if peer:
            return None
        if token is None:
            # What OAuth2PasswordBearer answers on the routes that only take a user
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return require_role(await user_from_token(db, token, token_service), self.allowed_roles)
