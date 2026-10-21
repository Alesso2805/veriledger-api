from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.core.config import settings
from backend.app.infrastructure.models.user import UserModel
from backend.app.main import app

pytestmark = pytest.mark.asyncio

MINE = {"miner_address": "m" * 64}


@pytest.fixture
def demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "demo_mode", True)
    # Blocks that take no time, so the mining limits are quick to reach
    monkeypatch.setattr(settings, "mining_difficulty", 1)


async def demo_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/auth/demo")
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def users(postgres: async_sessionmaker[AsyncSession]) -> int:
    async with postgres() as session:
        return await session.scalar(select(func.count()).select_from(UserModel)) or 0


async def test_one_network_gets_its_demo_accounts_per_hour_and_another_network_is_not_held_back(
    async_client: AsyncClient,
    postgres: async_sessionmaker[AsyncSession],
    demo_mode: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "demo_accounts_per_ip_per_hour", 2)

    allowed = [(await async_client.post("/auth/demo")).status_code for _ in range(2)]
    refused = await async_client.post("/auth/demo")
    transport = ASGITransport(app=app, client=("203.0.113.7", 50000))
    async with AsyncClient(transport=transport, base_url="http://test") as other_network:
        elsewhere = await other_network.post("/auth/demo")

    assert allowed == [201, 201]
    assert refused.status_code == 429
    assert refused.json()["detail"] == "Too many demo accounts from your network in the last hour; try again later"
    assert 3500 <= int(refused.headers["Retry-After"]) <= 3600
    assert elsewhere.status_code == 201
    assert await users(postgres) == 3


async def test_a_full_demo_says_so_until_the_oldest_demo_expires(
    async_client: AsyncClient,
    postgres: async_sessionmaker[AsyncSession],
    demo_mode: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "demo_max_active_accounts", 1)

    first = await async_client.post("/auth/demo")
    full = await async_client.post("/auth/demo")
    async with postgres() as session:
        await session.execute(update(UserModel).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
        await session.commit()
    after_it_expired = await async_client.post("/auth/demo")

    assert (first.status_code, after_it_expired.status_code) == (201, 201)
    assert (full.status_code, full.json()["detail"]) == (429, "The demo is full right now; try again later")
    # The first demo's 24 hours, give or take the test's own seconds
    assert 86_000 <= int(full.headers["Retry-After"]) <= 86_400
    assert await users(postgres) == 2


async def test_a_demo_account_mines_its_blocks_per_hour_and_a_normal_account_is_not_limited(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    demo_mode: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "demo_mines_per_hour", 2)
    as_demo = await demo_headers(async_client)

    demo_mines = [(await async_client.post("/blocks/mine", json=MINE, headers=as_demo)).status_code for _ in range(2)]
    refused = await async_client.post("/blocks/mine", json=MINE, headers=as_demo)
    admin_mines = [
        (await async_client.post("/blocks/mine", json=MINE, headers=admin_headers)).status_code for _ in range(3)
    ]

    assert demo_mines == [200, 200]
    assert refused.status_code == 429
    assert refused.json()["detail"] == "A demo account can mine 2 blocks per hour; try again later"
    assert 0 < int(refused.headers["Retry-After"]) <= 3600
    assert admin_mines == [200, 200, 200]


async def test_zero_turns_each_limit_off(
    async_client: AsyncClient,
    postgres: async_sessionmaker[AsyncSession],
    demo_mode: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("demo_accounts_per_ip_per_hour", "demo_max_active_accounts", "demo_mines_per_hour"):
        monkeypatch.setattr(settings, name, 0)

    # One more than each default: 5 accounts per hour, 10 blocks per hour
    accounts = [(await async_client.post("/auth/demo")).status_code for _ in range(6)]
    as_demo = await demo_headers(async_client)
    mines = [(await async_client.post("/blocks/mine", json=MINE, headers=as_demo)).status_code for _ in range(11)]

    assert accounts == [201] * 6
    assert mines == [200] * 11
    assert await users(postgres) == 7


async def test_a_limit_of_one_block_reads_in_the_singular(
    async_client: AsyncClient,
    postgres: async_sessionmaker[AsyncSession],
    demo_mode: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "demo_mines_per_hour", 1)
    as_demo = await demo_headers(async_client)

    first = await async_client.post("/blocks/mine", json=MINE, headers=as_demo)
    refused = await async_client.post("/blocks/mine", json=MINE, headers=as_demo)

    assert first.status_code == 200
    assert refused.json()["detail"] == "A demo account can mine 1 block per hour; try again later"
