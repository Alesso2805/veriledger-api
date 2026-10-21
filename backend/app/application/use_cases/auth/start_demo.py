import uuid
from datetime import UTC, datetime, timedelta

from backend.app.application.dto.user import TokenDTO
from backend.app.domain.entities.user import User, UserRole
from backend.app.domain.ports.repositories.user_repository import UserRepository
from backend.app.domain.ports.services.security import TokenService

# ADR-0006: a visitor's account lasts a day
DEMO_LIFETIME = timedelta(hours=24)


class StartDemoUseCase:
    def __init__(self, user_repo: UserRepository, token_service: TokenService):
        self.user_repo = user_repo
        self.token_service = token_service

    async def execute(self) -> TokenDTO:
        now = datetime.now(UTC)
        user = await self.user_repo.save(
            User(
                id=str(uuid.uuid4()),
                email=None,
                password_hash=None,
                role=UserRole.TRADER,
                created_at=now,
                updated_at=now,
                expires_at=now + DEMO_LIFETIME,
            )
        )
        token = self.token_service.create_access_token(
            subject=user.id, role=user.role.value, expires_at=user.expires_at, demo=True
        )
        return TokenDTO(access_token=token)
