import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.infrastructure import database
from backend.app.infrastructure.database import Base

# Never the app's database: the fixture drops every table. VLA-25 provides one in CI.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest_asyncio.fixture
async def postgres(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    if not TEST_DATABASE_URL.startswith("postgresql"):
        pytest.skip("needs TEST_DATABASE_URL pointing to a throwaway PostgreSQL")

    # NullPool: each test runs on its own event loop, and asyncpg connections cannot move between loops
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    # Swap the session factory, not get_db_session, so requests go through the real commit
    monkeypatch.setattr(database, "async_session_maker", session_maker)

    yield session_maker

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
