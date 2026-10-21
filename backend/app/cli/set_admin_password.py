import asyncio

import structlog

from backend.app.core.config import DEVELOPMENT_ADMIN_PASSWORD, settings
from backend.app.core.logger import setup_logging
from backend.app.domain.entities.user import UserRole
from backend.app.infrastructure import database
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from backend.app.infrastructure.security.password_hasher import PasswordHasherImpl

logger = structlog.get_logger()


async def set_admin_password() -> None:
    """Gives the admin of ADMIN_EMAIL the password ADMIN_PASSWORD (VLA-28), since the seed only creates it once."""
    setup_logging()
    if settings.app_env == "production" and settings.admin_password in ("", DEVELOPMENT_ADMIN_PASSWORD):
        raise SystemExit("ADMIN_PASSWORD must be set in production; the development password is refused")
    # The factory is read when the command runs, so tests can point it at their database
    async with database.async_session_maker() as session:
        user_repo = UserRepositoryImpl(session)
        admin = await user_repo.get_by_email(settings.admin_email)
        if admin is None or admin.role != UserRole.ADMIN:
            raise SystemExit(f"No admin has the email {settings.admin_email}")
        await user_repo.set_password_hash(admin.id, PasswordHasherImpl().hash_password(settings.admin_password))
        await session.commit()
    logger.info("Admin password changed", email=settings.admin_email)


if __name__ == "__main__":
    asyncio.run(set_admin_password())
