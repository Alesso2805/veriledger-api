from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.app.application.dto.user import UserCreateDTO  # noqa: F401  CI canary: breaks AR-03 on purpose
from backend.app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    future=True,
)

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    # One transaction per request: if the endpoint raises, the commit is skipped and closing the session rolls back
    async with async_session_maker() as session:
        yield session
        await session.commit()
