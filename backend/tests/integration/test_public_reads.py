import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.tests.integration.conftest import VECTORS, fund, submit

pytestmark = pytest.mark.asyncio

TRANSFER, TRANSFER_WITH_FEE = VECTORS[0], VECTORS[1]
WRITES = [
    ("POST", "/transactions"),
    ("POST", "/blocks/mine"),
    ("POST", "/nodes/register"),
    ("POST", "/nodes/resolve"),
    ("POST", "/users"),
]


async def test_blocks_transactions_and_peers_are_read_without_a_token(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    # Writes with the admin's token: a mined transfer, a pending one and a peer
    await fund(async_client, admin_headers, TRANSFER["fields"]["sender_address"])
    await fund(async_client, admin_headers, TRANSFER_WITH_FEE["fields"]["sender_address"])
    mined_tx = await submit(async_client, admin_headers, TRANSFER)
    block = (await async_client.post("/blocks/mine", json={"miner_address": "miner"}, headers=admin_headers)).json()
    pending_tx = await submit(async_client, admin_headers, TRANSFER_WITH_FEE)
    await async_client.post("/nodes/register", json={"url": "http://peer.example"}, headers=admin_headers)

    # Reads with no Authorization header at all
    blocks = await async_client.get("/blocks")
    full = await async_client.get("/blocks/full")
    by_hash = await async_client.get(f"/blocks/{block['block_hash']}")
    transaction = await async_client.get(f"/transactions/{mined_tx}")
    waiting = await async_client.get("/transactions?status=PENDING")
    nodes = await async_client.get("/nodes")

    assert [r.status_code for r in (blocks, full, by_hash, transaction, waiting, nodes)] == [200] * 6
    assert blocks.json()["total"] == 3
    assert full.json()["items"][0]["block_hash"] == block["block_hash"]
    assert mined_tx in {tx["tx_hash"] for tx in by_hash.json()["transactions"]}
    assert transaction.json()["block_hash"] == block["block_hash"]
    assert [tx["tx_hash"] for tx in waiting.json()["items"]] == [pending_tx]
    assert [node["url"] for node in nodes.json()] == ["http://peer.example"]


@pytest.mark.parametrize(("method", "path"), WRITES, ids=[path for _, path in WRITES])
async def test_every_write_still_needs_a_token(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], method: str, path: str
) -> None:
    response = await async_client.request(method, path, json={})

    assert response.status_code == 401


@pytest.mark.parametrize("query", ["/blocks?limit=101", "/blocks/full?limit=101", "/blocks?limit=0", "/blocks?skip=-1"])
async def test_public_block_pages_are_capped(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], query: str
) -> None:
    response = await async_client.get(query)

    assert response.status_code == 422
