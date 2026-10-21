import json
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio

VECTORS: list[dict[str, Any]] = json.loads(
    (Path(__file__).resolve().parents[3] / "docs" / "signing-vectors.json").read_text(encoding="utf-8")
)["vectors"]


async def fund(client: AsyncClient, headers: dict[str, str], address: str) -> None:
    # Mining an empty mempool pays the coinbase (50) to the miner, enough for every vector
    response = await client.post("/blocks/mine", json={"miner_address": address}, headers=headers)
    assert response.status_code == 200


@pytest.mark.parametrize("vector", VECTORS, ids=[vector["name"] for vector in VECTORS])
async def test_a_vector_signed_with_noble_is_accepted(
    async_client: AsyncClient,
    postgres: async_sessionmaker[AsyncSession],
    admin_headers: dict[str, str],
    vector: dict[str, Any],
) -> None:
    fields = vector["fields"]
    await fund(async_client, admin_headers, fields["sender_address"])

    response = await async_client.post(
        "/transactions", json={**fields, "signature": vector["signature"]}, headers=admin_headers
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"


async def test_a_vector_with_a_changed_amount_is_rejected(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    vector = VECTORS[0]
    await fund(async_client, admin_headers, vector["fields"]["sender_address"])

    body = {**vector["fields"], "amount": "11.00000000", "signature": vector["signature"]}
    response = await async_client.post("/transactions", json=body, headers=admin_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid transaction signature"


async def test_amounts_sent_as_numbers_are_rejected(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    # The body carries the strings that were signed (ADR-0004); a number would have to be formatted again
    vector = VECTORS[0]
    body = {**vector["fields"], "amount": 10, "fee": 0, "signature": vector["signature"]}
    response = await async_client.post("/transactions", json=body, headers=admin_headers)

    assert response.status_code == 422
