import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.domain.entities.user import UserRole
from backend.app.infrastructure.models.user import UserModel
from backend.app.infrastructure.security.password_hasher import PasswordHasherImpl

pytestmark = pytest.mark.asyncio

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password"
NEW_USER = {"email": "trader@example.com", "password": "trader-password", "role": "trader"}


async def admin_headers(client: AsyncClient, session_maker: async_sessionmaker[AsyncSession]) -> dict[str, str]:
    async with session_maker() as session:
        session.add(
            UserModel(
                id=str(uuid.uuid4()),
                email=ADMIN_EMAIL,
                password_hash=PasswordHasherImpl().hash_password(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
            )
        )
        await session.commit()
    response = await client.post("/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_created_user_is_saved_and_can_sign_in(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession]
) -> None:
    headers = await admin_headers(async_client, postgres)

    response = await async_client.post("/users", json=NEW_USER, headers=headers)
    assert response.status_code == 201

    # A new session sees only what the request committed
    async with postgres() as session:
        saved = (await session.execute(select(UserModel).where(UserModel.email == NEW_USER["email"]))).scalar_one()
    assert saved.role == UserRole.TRADER

    login = await async_client.post(
        "/auth/login", data={"username": NEW_USER["email"], "password": NEW_USER["password"]}
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


async def test_same_email_twice_is_rejected(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession]
) -> None:
    headers = await admin_headers(async_client, postgres)

    first = await async_client.post("/users", json=NEW_USER, headers=headers)
    second = await async_client.post("/users", json=NEW_USER, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 400
    assert second.json()["detail"] == "Email already registered"
    async with postgres() as session:
        count = await session.scalar(
            select(func.count()).select_from(UserModel).where(UserModel.email == NEW_USER["email"])
        )
    assert count == 1
