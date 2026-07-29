import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.infrastructure.database import Base, get_db_session

# Test database URL - using main DB for now
TEST_DATABASE_URL = settings.database_url

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)
async_session_maker_test = async_sessionmaker(
    engine_test, class_=AsyncSession, expire_on_commit=False
)

async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker_test() as session:
        yield session

app.dependency_overrides[get_db_session] = override_get_db_session

@pytest_asyncio.fixture(scope="session")
async def setup_database() -> AsyncGenerator[None, None]:
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
