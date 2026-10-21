import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.domain.entities.user import UserRole
from backend.app.infrastructure.models.user import UserModel

pytestmark = pytest.mark.asyncio

NEW_USER = {"email": "trader@example.com", "password": "trader-password", "role": "trader"}


async def test_created_user_is_saved_and_can_sign_in(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    response = await async_client.post("/users", json=NEW_USER, headers=admin_headers)
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
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    first = await async_client.post("/users", json=NEW_USER, headers=admin_headers)
    second = await async_client.post("/users", json=NEW_USER, headers=admin_headers)

    assert first.status_code == 201
    assert second.status_code == 400
    assert second.json()["detail"] == "Email already registered"
    async with postgres() as session:
        count = await session.scalar(
            select(func.count()).select_from(UserModel).where(UserModel.email == NEW_USER["email"])
        )
    assert count == 1


async def test_a_wrong_password_is_refused(async_client: AsyncClient, admin_headers: dict[str, str]) -> None:
    response = await async_client.post(
        "/auth/login", data={"username": "admin@example.com", "password": "not-the-password"}
    )

    assert (response.status_code, response.json()["detail"]) == (401, "Invalid credentials")
