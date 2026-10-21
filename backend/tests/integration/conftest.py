import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.domain.entities.user import UserRole
from backend.app.infrastructure import database
from backend.app.infrastructure.database import Base
from backend.app.infrastructure.models.user import UserModel
from backend.app.infrastructure.security.password_hasher import PasswordHasherImpl

# Never the app's database: the fixture drops every table. VLA-25 provides one in CI.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password"


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


@pytest_asyncio.fixture
async def admin_headers(async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession]) -> dict[str, str]:
    async with postgres() as session:
        session.add(
            UserModel(
                id=str(uuid.uuid4()),
                email=ADMIN_EMAIL,
                password_hash=PasswordHasherImpl().hash_password(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
            )
        )
        await session.commit()
    response = await async_client.post("/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
