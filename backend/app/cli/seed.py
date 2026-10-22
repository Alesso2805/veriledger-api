import asyncio

import structlog

from backend.app.application.dto.user import UserCreateDTO
from backend.app.application.use_cases.auth.register_user import RegisterUserUseCase
from backend.app.core.config import DEVELOPMENT_ADMIN_PASSWORD, settings
from backend.app.core.logger import setup_logging
from backend.app.domain.entities.user import UserRole
from backend.app.infrastructure import database
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from backend.app.infrastructure.security.password_hasher import PasswordHasherImpl

logger = structlog.get_logger()


async def seed_admin() -> bool:
    """Creates the admin of ADMIN_EMAIL unless it exists; True when this run created it."""
    setup_logging()
    # A known password on a public node's admin makes anyone its admin
    if settings.app_env == "production" and settings.admin_password in ("", DEVELOPMENT_ADMIN_PASSWORD):
        raise SystemExit("ADMIN_PASSWORD must be set in production; the development password is refused")
    # The factory is read when the command runs, so tests can point it at their database
    async with database.async_session_maker() as session:
        user_repo = UserRepositoryImpl(session)
        if await user_repo.get_by_email(settings.admin_email):
            logger.info("Admin user already exists", email=settings.admin_email)
            return False
        dto = UserCreateDTO(email=settings.admin_email, password=settings.admin_password, role=UserRole.ADMIN)
        await RegisterUserUseCase(user_repo, PasswordHasherImpl()).execute(dto)
        await session.commit()
        logger.info("Admin user seeded", email=settings.admin_email)
        return True


if __name__ == "__main__":
    asyncio.run(seed_admin())
