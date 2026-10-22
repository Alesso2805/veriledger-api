import asyncio
import json
import os
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.core.config import settings
from backend.app.domain.entities.user import UserRole
from backend.app.infrastructure import database
from backend.app.infrastructure.database import Base
from backend.app.infrastructure.limits.sliding_window import SlidingWindowLimiter
from backend.app.infrastructure.models.user import UserModel
from backend.app.infrastructure.security.password_hasher import PasswordHasherImpl
from backend.app.presentation.dependencies import limits

# Never the app's database: the fixture drops every table. CI provides one.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password"

VECTORS: list[dict[str, Any]] = json.loads(
    (Path(__file__).resolve().parents[3] / "docs" / "signing-vectors.json").read_text(encoding="utf-8")
)["vectors"]


async def fund(client: AsyncClient, headers: dict[str, str], address: str) -> None:
    # Mining an empty mempool pays the coinbase (50) to the miner, enough for every vector
    response = await client.post("/blocks/mine", json={"miner_address": address}, headers=headers)
    assert response.status_code == 200


async def submit(client: AsyncClient, headers: dict[str, str], vector: dict[str, Any]) -> str:
    body = {**vector["fields"], "signature": vector["signature"]}
    response = await client.post("/transactions", json=body, headers=headers)
    assert response.status_code == 201
    tx_hash: str = response.json()["tx_hash"]
    return tx_hash


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    # The limiter and the mining lock live as long as the process; each test starts from nothing
    monkeypatch.setattr(limits, "limiter", SlidingWindowLimiter())
    monkeypatch.setattr(limits, "mining_lock", asyncio.Lock())


@pytest.fixture
def private_peers(monkeypatch: pytest.MonkeyPatch) -> None:
    # Peers on reserved names like peer.example, which only ALLOW_PRIVATE_PEERS lets through, as in Compose
    monkeypatch.setattr(settings, "allow_private_peers", True)


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
