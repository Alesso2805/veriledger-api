import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

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


async def database_answers(timeout: float = 2.0) -> bool:
    """Whether the database runs a query within the timeout, for /health (VLA-26)."""

    async def ping() -> None:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(ping(), timeout=timeout)
    except (OSError, SQLAlchemyError, TimeoutError):
        return False
    return True
