import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.tests.integration.conftest import VECTORS, fund, submit

pytestmark = pytest.mark.asyncio

BY_NAME = {vector["name"]: vector for vector in VECTORS}


async def test_the_mempool_lists_newest_first_with_the_real_total(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    await fund(async_client, admin_headers, BY_NAME["transfer"]["fields"]["sender_address"])
    await fund(async_client, admin_headers, BY_NAME["transfer_with_fee"]["fields"]["sender_address"])
    confirmed = await submit(async_client, admin_headers, BY_NAME["transfer"])
    await fund(async_client, admin_headers, "miner")  # mines the transfer, so one transaction is not pending
    pending = [
        await submit(async_client, admin_headers, BY_NAME[name])
        for name in ("transfer_with_fee", "smallest_amount", "notarization")
    ]

    first = (await async_client.get("/transactions?status=PENDING&limit=2", headers=admin_headers)).json()
    rest = (await async_client.get("/transactions?status=PENDING&skip=2&limit=2", headers=admin_headers)).json()

    newest_first = pending[::-1]
    assert [tx["tx_hash"] for tx in first["items"]] == newest_first[:2]
    assert [tx["tx_hash"] for tx in rest["items"]] == newest_first[2:]
    assert (first["total"], first["page"], rest["page"]) == (3, 1, 2)
    assert confirmed not in [tx["tx_hash"] for tx in first["items"] + rest["items"]]
    assert first["items"][0]["payload"] == BY_NAME["notarization"]["fields"]["payload"]
    assert all(tx["status"] == "PENDING" and tx["block_number"] is None for tx in first["items"] + rest["items"])


@pytest.mark.parametrize("query", ["limit=101", "limit=0", "skip=-1", "status=CONFIRMED"])
async def test_out_of_bounds_queries_are_refused(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str], query: str
) -> None:
    response = await async_client.get(f"/transactions?{query}", headers=admin_headers)

    assert response.status_code == 422
