import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.cli.seed import seed_admin
from backend.app.core.config import settings
from backend.app.domain.entities.user import UserRole
from backend.app.infrastructure.models.user import UserModel

pytestmark = pytest.mark.asyncio

EMAIL = "operator@example.com"
PASSWORD = "a-long-operator-password"


@pytest.fixture
def credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_email", EMAIL)
    monkeypatch.setattr(settings, "admin_password", PASSWORD)


async def users(postgres: async_sessionmaker[AsyncSession]) -> list[tuple[str | None, UserRole]]:
    async with postgres() as session:
        rows = (await session.execute(select(UserModel.email, UserModel.role))).all()
        return [(email, role) for email, role in rows]


async def test_the_seed_creates_the_admin_of_the_environment_who_can_sign_in(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], credentials: None
) -> None:
    assert await seed_admin() is True

    login = await async_client.post("/auth/login", data={"username": EMAIL, "password": PASSWORD})

    assert await users(postgres) == [(EMAIL, UserRole.ADMIN)]
    assert login.status_code == 200


async def test_running_the_seed_again_changes_nothing(
    postgres: async_sessionmaker[AsyncSession], credentials: None
) -> None:
    assert (await seed_admin(), await seed_admin()) == (True, False)
    assert await users(postgres) == [(EMAIL, UserRole.ADMIN)]


@pytest.mark.parametrize("password", ["adminpassword123", ""], ids=["the development password", "empty"])
async def test_production_refuses_a_known_or_empty_password_and_creates_nobody(
    postgres: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch, password: str
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "admin_password", password)

    with pytest.raises(SystemExit, match="ADMIN_PASSWORD must be set in production"):
        await seed_admin()

    assert await users(postgres) == []


async def test_production_seeds_an_admin_with_its_own_password(
    postgres: async_sessionmaker[AsyncSession], credentials: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")

    assert await seed_admin() is True
    assert await users(postgres) == [(EMAIL, UserRole.ADMIN)]
