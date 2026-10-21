import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.tests.integration.conftest import VECTORS, fund, submit

pytestmark = pytest.mark.asyncio

BY_NAME = {vector["name"]: vector for vector in VECTORS}
ALICE = BY_NAME["transfer"]["fields"]["sender_address"]
BOB = BY_NAME["transfer_with_fee"]["fields"]["sender_address"]
CAROL = BY_NAME["notarization"]["fields"]["sender_address"]


async def test_an_address_lists_what_it_sent_and_received_newest_first(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    await fund(async_client, admin_headers, ALICE)  # block 0 pays alice's coinbase
    await fund(async_client, admin_headers, BOB)
    sent = await submit(async_client, admin_headers, BY_NAME["transfer"])  # alice → bob
    received = await submit(async_client, admin_headers, BY_NAME["transfer_with_fee"])  # bob → alice

    # No token: the activity is public, like the balance
    activity = (await async_client.get(f"/wallets/{ALICE}/transactions")).json()
    first = (await async_client.get(f"/wallets/{ALICE}/transactions?limit=2")).json()
    rest = (await async_client.get(f"/wallets/{ALICE}/transactions?skip=2&limit=2")).json()

    items = activity["items"]
    assert [tx["tx_hash"] for tx in items[:2]] == [received, sent]
    assert [(tx["status"], tx["block_number"]) for tx in items[:2]] == [("PENDING", None), ("PENDING", None)]
    coinbase = items[2]
    assert (coinbase["sender_address"], coinbase["status"], coinbase["block_number"]) == ("SYSTEM", "CONFIRMED", 0)
    assert coinbase["block_hash"] is not None
    assert activity["total"] == 3
    assert [tx["tx_hash"] for tx in first["items"] + rest["items"]] == [tx["tx_hash"] for tx in items]


async def test_an_address_with_no_transactions_has_an_empty_activity(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession]
) -> None:
    activity = (await async_client.get(f"/wallets/{CAROL}/transactions")).json()

    assert (activity["items"], activity["total"]) == ([], 0)


async def test_a_notarization_appears_once_although_it_sends_to_its_own_sender(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    notarized = await submit(async_client, admin_headers, BY_NAME["notarization"])

    activity = (await async_client.get(f"/wallets/{CAROL}/transactions")).json()

    assert ([tx["tx_hash"] for tx in activity["items"]], activity["total"]) == ([notarized], 1)


@pytest.mark.parametrize("query", ["limit=101", "limit=0", "skip=-1"])
async def test_activity_pages_are_capped(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], query: str
) -> None:
    response = await async_client.get(f"/wallets/{ALICE}/transactions?{query}")

    assert response.status_code == 422
