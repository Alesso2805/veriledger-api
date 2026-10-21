from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.tests.integration.conftest import VECTORS, fund

pytestmark = pytest.mark.asyncio

TRANSFER = next(vector for vector in VECTORS if vector["name"] == "transfer")
NOTARIZATION = next(vector for vector in VECTORS if vector["name"] == "notarization")


async def submit(client: AsyncClient, headers: dict[str, str], vector: dict[str, Any]) -> str:
    body = {**vector["fields"], "signature": vector["signature"]}
    response = await client.post("/transactions", json=body, headers=headers)
    assert response.status_code == 201
    tx_hash: str = response.json()["tx_hash"]
    return tx_hash


async def mine(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    response = await client.post("/blocks/mine", json={"miner_address": "miner"}, headers=headers)
    assert response.status_code == 200
    block: dict[str, Any] = response.json()
    return block


async def test_a_block_is_found_by_its_hash_with_its_transactions(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    await fund(async_client, admin_headers, TRANSFER["fields"]["sender_address"])
    tx_hash = await submit(async_client, admin_headers, TRANSFER)
    mined = await mine(async_client, admin_headers)

    response = await async_client.get(f"/blocks/{mined['block_hash']}", headers=admin_headers)

    assert response.status_code == 200
    block = response.json()
    assert block["block_number"] == mined["block_number"]
    # The coinbase and the transfer, by hash, in the mine response and in the block
    assert len(mined["transaction_hashes"]) == len(mined["transaction_ids"]) == 2
    assert tx_hash in mined["transaction_hashes"]
    assert {tx["tx_hash"] for tx in block["transactions"]} == set(mined["transaction_hashes"])


async def test_an_unknown_block_hash_answers_404(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    response = await async_client.get(f"/blocks/{'0' * 64}", headers=admin_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Block not found"


async def test_block_lists_carry_transaction_hashes_and_the_real_total(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    for _ in range(3):
        await mine(async_client, admin_headers)

    page = (await async_client.get("/blocks?limit=1", headers=admin_headers)).json()
    full = (await async_client.get("/blocks/full?limit=1", headers=admin_headers)).json()

    assert (len(page["items"]), page["total"]) == (1, 3)
    assert (len(full["items"]), full["total"]) == (1, 3)
    assert page["items"][0]["transaction_hashes"] == [full["items"][0]["transactions"][0]["tx_hash"]]


async def test_a_transaction_shows_its_block_once_mined(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    await fund(async_client, admin_headers, TRANSFER["fields"]["sender_address"])
    tx_hash = await submit(async_client, admin_headers, TRANSFER)

    pending = (await async_client.get(f"/transactions/{tx_hash}", headers=admin_headers)).json()
    mined = await mine(async_client, admin_headers)
    confirmed = (await async_client.get(f"/transactions/{tx_hash}", headers=admin_headers)).json()

    assert (pending["status"], pending["block_number"], pending["block_hash"]) == ("PENDING", None, None)
    assert confirmed["status"] == "CONFIRMED"
    assert (confirmed["block_number"], confirmed["block_hash"]) == (mined["block_number"], mined["block_hash"])


async def test_full_blocks_keep_the_notarized_payload(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    # A notarization moves no funds and pays no fee, so its sender needs no balance
    await submit(async_client, admin_headers, NOTARIZATION)
    mined = await mine(async_client, admin_headers)

    full = (await async_client.get("/blocks/full", headers=admin_headers)).json()
    by_hash = (await async_client.get(f"/blocks/{mined['block_hash']}", headers=admin_headers)).json()

    payload = NOTARIZATION["fields"]["payload"]
    assert payload in {tx["payload"] for tx in full["items"][0]["transactions"]}
    assert payload in {tx["payload"] for tx in by_hash["transactions"]}
