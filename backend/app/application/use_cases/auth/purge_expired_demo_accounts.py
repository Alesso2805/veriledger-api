from datetime import UTC, datetime

from backend.app.domain.ports.repositories.user_repository import UserRepository


class PurgeExpiredDemoAccountsUseCase:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def execute(self) -> int:
        # The accounts go; what they recorded stays on the chain for good (ADR-0006)
        return await self.user_repo.delete_expired(datetime.now(UTC))
