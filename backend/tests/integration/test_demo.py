import re
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.cli.purge_demo_accounts import purge_demo_accounts
from backend.app.core.config import settings
from backend.app.infrastructure.models.block_model import BlockModel
from backend.app.infrastructure.models.transaction_model import TransactionModel
from backend.app.infrastructure.models.user import UserModel
from backend.app.infrastructure.security.jwt_service import JWTTokenService
from backend.tests.integration.conftest import ADMIN_EMAIL, VECTORS, fund, submit

pytestmark = pytest.mark.asyncio

TRANSFER = VECTORS[0]


@pytest.fixture
def demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "demo_mode", True)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def start_demo(client: AsyncClient) -> str:
    response = await client.post("/auth/demo")
    assert response.status_code == 201
    token: str = response.json()["access_token"]
    return token


async def expire(postgres: async_sessionmaker[AsyncSession], user_id: str) -> None:
    async with postgres() as session:
        past = datetime.now(UTC) - timedelta(minutes=1)
        await session.execute(update(UserModel).where(UserModel.id == user_id).values(expires_at=past))
        await session.commit()


async def test_a_demo_is_a_trader_named_guest_for_24_hours_and_its_token_says_so(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], demo_mode: None
) -> None:
    response = await async_client.post("/auth/demo")
    token = response.json()["access_token"]
    me = (await async_client.get("/auth/me", headers=bearer(token))).json()

    assert (response.status_code, response.json()["token_type"]) == (201, "bearer")
    assert (me["email"], me["role"]) == (None, "trader")
    assert re.fullmatch(r"Guest [0-9A-F]{4}", me["display_name"])
    expires_at = datetime.fromisoformat(me["expires_at"])
    assert abs(expires_at - (datetime.now(UTC) + timedelta(hours=24))) < timedelta(minutes=1)
    claims = JWTTokenService().verify_token(token)
    assert (claims["demo"], claims["exp"], claims["role"]) == (True, int(expires_at.timestamp()), "trader")


async def test_a_normal_account_is_named_by_its_email_and_does_not_expire(
    async_client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    me = (await async_client.get("/auth/me", headers=admin_headers)).json()

    assert (me["email"], me["display_name"], me["expires_at"]) == (ADMIN_EMAIL, ADMIN_EMAIL, None)


async def test_without_demo_mode_there_is_no_demo(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "demo_mode", False)

    response = await async_client.post("/auth/demo")
    health = (await async_client.get("/health")).json()

    assert (response.status_code, response.json()["detail"]) == (404, "Not Found")
    assert health["demo_mode"] is False
    async with postgres() as session:
        assert await session.scalar(select(func.count()).select_from(UserModel)) == 0


async def test_health_says_when_the_demo_is_on(async_client: AsyncClient, demo_mode: None) -> None:
    assert (await async_client.get("/health")).json()["demo_mode"] is True


async def test_an_expired_demo_is_refused_like_any_expired_token(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], demo_mode: None
) -> None:
    token = await start_demo(async_client)
    user_id = (await async_client.get("/auth/me", headers=bearer(token))).json()["id"]
    await expire(postgres, user_id)

    me = await async_client.get("/auth/me", headers=bearer(token))
    mined = await async_client.post("/blocks/mine", json={"miner_address": "m" * 64}, headers=bearer(token))

    assert (me.status_code, me.json()["detail"]) == (401, "Could not validate credentials")
    assert mined.status_code == 401


async def test_the_cleanup_deletes_only_expired_demo_accounts_and_the_chain_keeps_what_they_did(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    postgres: async_sessionmaker[AsyncSession],
    demo_mode: None,
) -> None:
    ended, active = await start_demo(async_client), await start_demo(async_client)
    # The demo that ends mines and sends, as a visitor would
    await fund(async_client, bearer(ended), TRANSFER["fields"]["sender_address"])
    tx_hash = await submit(async_client, bearer(ended), TRANSFER)
    await expire(postgres, (await async_client.get("/auth/me", headers=bearer(ended))).json()["id"])

    assert await purge_demo_accounts() == 1

    async with postgres() as session:
        users = (await session.execute(select(UserModel.email, UserModel.expires_at))).all()
        blocks = await session.scalar(select(func.count()).select_from(BlockModel))
        transactions = await session.scalar(select(func.count()).select_from(TransactionModel))
    assert sorted(email or "demo" for email, _ in users) == sorted([ADMIN_EMAIL, "demo"])
    assert (blocks, transactions) == (1, 2)
    assert (await async_client.get(f"/transactions/{tx_hash}")).status_code == 200
    assert (await async_client.get("/auth/me", headers=bearer(active))).status_code == 200
