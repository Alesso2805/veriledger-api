import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.cli.seed import seed_admin
from backend.app.cli.set_admin_password import set_admin_password
from backend.app.core.config import settings

pytestmark = pytest.mark.asyncio

EMAIL = "operator@example.com"
OLD, NEW = "the-first-long-password", "the-rotated-long-password"


async def sign_in(client: AsyncClient, password: str) -> int:
    response = await client.post("/auth/login", data={"username": EMAIL, "password": password})
    return response.status_code


@pytest_asyncio.fixture
async def seeded_admin(postgres: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_email", EMAIL)
    monkeypatch.setattr(settings, "admin_password", OLD)
    await seed_admin()


async def test_the_admin_signs_in_with_the_new_password_and_no_longer_with_the_old(
    async_client: AsyncClient, seeded_admin: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "admin_password", NEW)

    await set_admin_password()

    assert (await sign_in(async_client, NEW), await sign_in(async_client, OLD)) == (200, 401)


async def test_an_email_that_is_not_an_admins_is_refused(seeded_admin: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_email", "someone-else@example.com")

    with pytest.raises(SystemExit, match="No admin has the email someone-else@example.com"):
        await set_admin_password()


@pytest.mark.parametrize("password", ["adminpassword123", ""], ids=["the development password", "empty"])
async def test_production_refuses_a_known_or_empty_password(
    async_client: AsyncClient, seeded_admin: None, monkeypatch: pytest.MonkeyPatch, password: str
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "admin_password", password)

    with pytest.raises(SystemExit, match="ADMIN_PASSWORD must be set in production"):
        await set_admin_password()

    assert await sign_in(async_client, OLD) == 200
