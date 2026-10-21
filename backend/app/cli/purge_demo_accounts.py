import asyncio

import structlog

from backend.app.application.use_cases.auth.purge_expired_demo_accounts import PurgeExpiredDemoAccountsUseCase
from backend.app.core.logger import setup_logging
from backend.app.infrastructure import database
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl

logger = structlog.get_logger()


async def purge_demo_accounts() -> int:
    setup_logging()
    # The factory is read when the command runs, so tests can point it at their database
    async with database.async_session_maker() as session:
        deleted = await PurgeExpiredDemoAccountsUseCase(UserRepositoryImpl(session)).execute()
        await session.commit()
    logger.info("Expired demo accounts deleted", count=deleted)
    return deleted


if __name__ == "__main__":
    asyncio.run(purge_demo_accounts())
