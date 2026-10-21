import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.errors import NonceConflictError
from backend.app.infrastructure.models.transaction_model import TransactionModel
from backend.app.infrastructure.repositories.transaction_repository_impl import TransactionRepositoryImpl
from backend.tests.integration.conftest import VECTORS, fund, submit

pytestmark = pytest.mark.asyncio

BY_NAME = {vector["name"]: vector for vector in VECTORS}
ALICE = BY_NAME["transfer"]["fields"]["sender_address"]


def body(vector: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return {**vector["fields"], "signature": vector["signature"], **changes}


async def sent_by(session_maker: async_sessionmaker[AsyncSession], address: str) -> int:
    async with session_maker() as session:
        count = await session.scalar(select(func.count()).where(TransactionModel.sender_address == address))
    return int(count or 0)


async def test_the_next_nonce_starts_at_one_and_follows_each_transaction(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    before = (await async_client.get(f"/wallets/{ALICE}/nonce")).json()
    await fund(async_client, admin_headers, ALICE)
    await submit(async_client, admin_headers, BY_NAME["transfer"])
    after = (await async_client.get(f"/wallets/{ALICE}/nonce")).json()

    assert before == {"address": ALICE, "nonce": 1}
    assert after == {"address": ALICE, "nonce": 2}


async def test_a_replayed_request_body_creates_nothing(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    await fund(async_client, admin_headers, ALICE)
    await submit(async_client, admin_headers, BY_NAME["transfer"])

    replay = await async_client.post("/transactions", json=body(BY_NAME["transfer"]), headers=admin_headers)

    assert replay.status_code == 409
    assert replay.json()["detail"] == "Nonce 1 is not the next one for this sender; the next is 2"
    assert await sent_by(postgres, ALICE) == 1


async def test_a_skipped_nonce_is_a_conflict(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    # Alice's second vector, sent before her first
    await fund(async_client, admin_headers, ALICE)

    response = await async_client.post("/transactions", json=body(BY_NAME["smallest_amount"]), headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Nonce 2 is not the next one for this sender; the next is 1"
    assert await sent_by(postgres, ALICE) == 0


async def test_two_transactions_racing_for_one_nonce_keep_the_first(
    postgres: async_sessionmaker[AsyncSession],
) -> None:
    # Both passed the check at once; the unique constraint is what stops the second
    def transaction(tx_hash: str) -> Transaction:
        return Transaction(
            id=str(uuid.uuid4()),
            sender_address=ALICE,
            receiver_address="r",
            amount=1.0,
            fee=0.0,
            status=TransactionStatus.PENDING,
            timestamp=datetime.now(UTC),
            signature="sig",
            tx_hash=tx_hash,
            nonce=1,
        )

    async with postgres() as session:
        repo = TransactionRepositoryImpl(session)
        await repo.create(transaction("first"))
        with pytest.raises(NonceConflictError, match="Nonce 1 was just used"):
            await repo.create(transaction("second"))


@pytest.mark.parametrize("nonce", [None, 0, "1", 1.5], ids=["missing", "zero", "string", "float"])
async def test_a_nonce_that_is_not_a_positive_integer_is_refused(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str], nonce: Any
) -> None:
    request = body(BY_NAME["transfer"])
    if nonce is None:
        del request["nonce"]
    else:
        request["nonce"] = nonce

    response = await async_client.post("/transactions", json=request, headers=admin_headers)

    assert response.status_code == 422
