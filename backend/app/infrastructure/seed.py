import asyncio

import structlog

from backend.app.application.dto.user import UserCreateDTO
from backend.app.application.use_cases.auth.register_user import RegisterUserUseCase
from backend.app.core.logger import setup_logging
from backend.app.domain.entities.user import UserRole
from backend.app.infrastructure.database import async_session_maker
from backend.app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from backend.app.infrastructure.security.password_hasher import PasswordHasherImpl

logger = structlog.get_logger()


async def seed_admin() -> None:
    setup_logging()
    async with async_session_maker() as session:
        user_repo = UserRepositoryImpl(session)
        hasher = PasswordHasherImpl()
        use_case = RegisterUserUseCase(user_repo, hasher)

        # Check if admin exists
        existing_admin = await user_repo.get_by_email("admin@veriledger.com")
        if existing_admin:
            logger.info("Admin user already exists")
            return

        dto = UserCreateDTO(email="admin@veriledger.com", password="adminpassword123", role=UserRole.ADMIN)

        await use_case.execute(dto)
        await session.commit()
        logger.info("Admin user seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_admin())
