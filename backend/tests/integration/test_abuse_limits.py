import asyncio
import threading

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.core.config import settings
from backend.app.domain.entities.block import Block
from backend.app.infrastructure.consensus.pow_service import ProofOfWorkServiceImpl
from backend.app.main import app
from backend.tests.integration.conftest import VECTORS, fund

pytestmark = pytest.mark.asyncio

BY_NAME = {vector["name"]: vector for vector in VECTORS}
TRANSFER, NEXT_TRANSFER = BY_NAME["transfer"], BY_NAME["smallest_amount"]
WRONG_PASSWORD = {"username": "nobody@example.com", "password": "not-the-password"}
MINE = {"miner_address": "m" * 64}


def body(vector: dict[str, object]) -> dict[str, object]:
    fields = vector["fields"]
    assert isinstance(fields, dict)
    return {**fields, "signature": vector["signature"]}


async def test_sign_in_attempts_are_limited_per_address_and_another_address_is_not_held_back(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "login_attempts_per_minute", 2)

    tried = [(await async_client.post("/auth/login", data=WRONG_PASSWORD)).status_code for _ in range(2)]
    refused = await async_client.post("/auth/login", data=WRONG_PASSWORD)
    transport = ASGITransport(app=app, client=("203.0.113.9", 40000))
    async with AsyncClient(transport=transport, base_url="http://test") as elsewhere:
        other = await elsewhere.post("/auth/login", data=WRONG_PASSWORD)

    assert tried == [401, 401]
    assert refused.status_code == 429
    assert refused.json()["detail"] == "Too many sign-in attempts from your network; try again in a minute"
    assert 0 < int(refused.headers["Retry-After"]) <= 60
    assert other.status_code == 401


async def test_transactions_are_limited_per_sender_and_a_peers_relay_is_not(
    async_client: AsyncClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "transactions_per_sender_per_minute", 1)
    monkeypatch.setattr(settings, "peer_token", "peer-token-for-tests")
    await fund(async_client, admin_headers, TRANSFER["fields"]["sender_address"])

    first = await async_client.post("/transactions", json=body(TRANSFER), headers=admin_headers)
    refused = await async_client.post("/transactions", json=body(NEXT_TRANSFER), headers=admin_headers)
    relayed = await async_client.post(
        "/transactions", json=body(NEXT_TRANSFER), headers={"X-Peer-Token": "peer-token-for-tests"}
    )

    assert first.status_code == 201
    assert refused.status_code == 429
    assert refused.json()["detail"] == "Too many transactions from this sender; try again in a minute"
    assert 0 < int(refused.headers["Retry-After"]) <= 60
    assert relayed.status_code == 201


async def test_a_second_mine_while_one_runs_answers_429_at_once(
    async_client: AsyncClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    started, release = threading.Event(), threading.Event()
    search = ProofOfWorkServiceImpl._search

    # Holds the first block's search while the second request arrives
    def held_search(self: ProofOfWorkServiceImpl, block: Block, difficulty: int) -> tuple[int, str]:
        started.set()
        release.wait(timeout=5)
        return search(self, block, difficulty)

    monkeypatch.setattr(ProofOfWorkServiceImpl, "_search", held_search)
    monkeypatch.setattr(settings, "mining_difficulty", 1)

    first = asyncio.create_task(async_client.post("/blocks/mine", json=MINE, headers=admin_headers))
    while not started.is_set() and not first.done():
        await asyncio.sleep(0.01)
    second = await async_client.post("/blocks/mine", json=MINE, headers=admin_headers)
    release.set()

    assert (await first).status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "A block is being mined on this node; try again in a moment"
    assert second.headers["Retry-After"] == "1"


async def test_zero_and_false_turn_the_limits_off(
    async_client: AsyncClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "login_attempts_per_minute", 0)
    monkeypatch.setattr(settings, "transactions_per_sender_per_minute", 0)
    monkeypatch.setattr(settings, "mine_one_at_a_time", False)
    await fund(async_client, admin_headers, TRANSFER["fields"]["sender_address"])

    sign_ins = [(await async_client.post("/auth/login", data=WRONG_PASSWORD)).status_code for _ in range(6)]
    transactions = [
        (await async_client.post("/transactions", json=body(vector), headers=admin_headers)).status_code
        for vector in (TRANSFER, NEXT_TRANSFER)
    ]

    assert sign_ins == [401] * 6
    assert transactions == [201, 201]
