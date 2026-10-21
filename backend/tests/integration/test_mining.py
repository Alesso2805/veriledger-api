import asyncio
import threading

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.core.config import settings
from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.infrastructure.consensus.pow_service import ProofOfWorkServiceImpl
from backend.app.infrastructure.models.block_model import BlockModel
from backend.app.infrastructure.models.transaction_model import TransactionModel
from backend.app.infrastructure.repositories.block_repository_impl import BlockRepositoryImpl
from backend.app.infrastructure.repositories.transaction_repository_impl import TransactionRepositoryImpl
from backend.tests.integration.conftest import VECTORS, fund, submit

pytestmark = pytest.mark.asyncio

TRANSFER = VECTORS[0]
MINER = "m" * 64


async def mine(client: AsyncClient, headers: dict[str, str]) -> Response:
    return await client.post("/blocks/mine", json={"miner_address": MINER}, headers=headers)


async def written(postgres: async_sessionmaker[AsyncSession]) -> tuple[int, int, int]:
    """Blocks, coinbases and pending transactions in the database."""
    async with postgres() as session:
        blocks = await session.scalar(select(func.count()).select_from(BlockModel))
        coinbases = await session.scalar(
            select(func.count()).select_from(TransactionModel).where(TransactionModel.sender_address == "SYSTEM")
        )
        pending = await session.scalar(
            select(func.count())
            .select_from(TransactionModel)
            .where(TransactionModel.status == TransactionStatus.PENDING)
        )
    return blocks or 0, coinbases or 0, pending or 0


async def test_a_failure_while_confirming_leaves_nothing_written(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    postgres: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await fund(async_client, admin_headers, TRANSFER["fields"]["sender_address"])
    await submit(async_client, admin_headers, TRANSFER)
    assert await written(postgres) == (1, 1, 1)

    # The block and the coinbase are already flushed when the first confirmation fails
    async def lost_connection(self: TransactionRepositoryImpl, transaction: Transaction) -> Transaction:
        raise ConnectionError("the database went away")

    monkeypatch.setattr(TransactionRepositoryImpl, "update", lost_connection)

    with pytest.raises(ConnectionError):
        await mine(async_client, admin_headers)

    assert await written(postgres) == (1, 1, 1)


async def test_a_block_mined_on_a_stale_latest_block_answers_409_and_writes_nothing(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    postgres: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await fund(async_client, admin_headers, MINER)

    # As if block 0 had been committed just after this request read the latest block
    async def before_block_0(self: BlockRepositoryImpl) -> Block | None:
        return None

    monkeypatch.setattr(BlockRepositoryImpl, "get_latest_block", before_block_0)

    response = await mine(async_client, admin_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Block 0 was just mined by another request; mine again"
    assert await written(postgres) == (1, 1, 0)


async def test_simultaneous_mines_give_consecutive_blocks_or_409_with_one_coinbase_each(
    async_client: AsyncClient, admin_headers: dict[str, str], postgres: async_sessionmaker[AsyncSession]
) -> None:
    await fund(async_client, admin_headers, TRANSFER["fields"]["sender_address"])
    tx_hash = await submit(async_client, admin_headers, TRANSFER)

    responses = await asyncio.gather(*[mine(async_client, admin_headers) for _ in range(4)])

    statuses = [response.status_code for response in responses]
    assert set(statuses) <= {200, 409} and 200 in statuses
    mined = [response.json() for response in responses if response.status_code == 200]
    assert sorted(block["block_number"] for block in mined) == list(range(1, len(mined) + 1))
    assert await written(postgres) == (1 + len(mined), 1 + len(mined), 0)
    # The transfer is in exactly one block, and it is the block its row points to
    holders = [block["block_hash"] for block in mined if tx_hash in block["transaction_hashes"]]
    assert holders == [(await async_client.get(f"/transactions/{tx_hash}")).json()["block_hash"]]


async def test_health_answers_while_the_proof_of_work_runs(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    postgres: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started, release = threading.Event(), threading.Event()
    events: list[str] = []
    search = ProofOfWorkServiceImpl._search

    # Holds the search until /health has answered. On the event loop it would hold /health instead, for 5 s
    def held_search(self: ProofOfWorkServiceImpl, block: Block, difficulty: int) -> tuple[int, str]:
        started.set()
        release.wait(timeout=5)
        events.append("proof of work done")
        return search(self, block, difficulty)

    monkeypatch.setattr(ProofOfWorkServiceImpl, "_search", held_search)

    mining = asyncio.create_task(mine(async_client, admin_headers))
    while not started.is_set() and not mining.done():
        await asyncio.sleep(0.01)
    health = await async_client.get("/health")
    events.append("health answered")
    release.set()

    assert ((await mining).status_code, health.status_code) == (200, 200)
    assert events == ["health answered", "proof of work done"]


async def test_the_difficulty_and_the_reward_come_from_the_settings(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    postgres: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    difficulties: list[int] = []
    search = ProofOfWorkServiceImpl._search

    def recording_search(self: ProofOfWorkServiceImpl, block: Block, difficulty: int) -> tuple[int, str]:
        difficulties.append(difficulty)
        return search(self, block, difficulty)

    monkeypatch.setattr(ProofOfWorkServiceImpl, "_search", recording_search)
    monkeypatch.setattr(settings, "mining_difficulty", 2)
    monkeypatch.setattr(settings, "mining_reward", 7.5)

    block = (await mine(async_client, admin_headers)).json()

    assert difficulties == [2]
    assert block["block_hash"].startswith("00")
    assert (await async_client.get(f"/wallets/{MINER}/balance")).json()["balance"] == 7.5
