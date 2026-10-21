from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app.domain.entities.transaction import TransactionStatus
from backend.app.infrastructure.database import Base
from backend.app.infrastructure.models.block_model import BlockModel
from backend.app.infrastructure.models.transaction_model import TransactionModel
from backend.app.infrastructure.repositories.block_repository_impl import BlockRepositoryImpl


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    # StaticPool keeps a single connection, so the in-memory database survives between statements
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_replace_chain_parses_peer_timestamps(session: AsyncSession) -> None:
    # Peers serialize datetimes with Pydantic, which writes UTC either as "Z" or as "+00:00"
    chain = [
        {
            "id": "block-1",
            "block_number": 1,
            "previous_hash": "0" * 64,
            "timestamp": "2026-10-20T12:00:00Z",
            "nonce": 42,
            "block_hash": "0000" + "a" * 60,
            "transactions": [
                {
                    "id": "tx-1",
                    "sender_address": "SYSTEM",
                    "receiver_address": "b" * 64,
                    "amount": 50.0,
                    "fee": 0.0,
                    "status": "CONFIRMED",
                    "timestamp": "2026-10-20T11:59:59.123456+00:00",
                    "signature": "COINBASE",
                    "tx_hash": "c" * 64,
                }
            ],
        }
    ]

    await BlockRepositoryImpl(session).replace_chain(chain)

    session.expunge_all()
    block = (await session.execute(select(BlockModel))).scalar_one()
    tx = (await session.execute(select(TransactionModel))).scalar_one()
    # SQLite drops the UTC offset, so only the wall-clock time is compared
    assert block.timestamp.replace(tzinfo=None) == datetime(2026, 10, 20, 12, 0)
    assert tx.timestamp.replace(tzinfo=None) == datetime(2026, 10, 20, 11, 59, 59, 123456)
    assert tx.block_id == block.id


def peer_transaction(tx_id: str, sender: str, nonce: int, **fields: Any) -> dict[str, Any]:
    return {
        "id": tx_id,
        "sender_address": sender,
        "receiver_address": "b" * 64,
        "amount": 1.0,
        "fee": 0.0,
        "status": "CONFIRMED",
        "timestamp": "2026-10-20T12:00:00+00:00",
        "signature": "sig",
        "tx_hash": f"hash-{tx_id}",
        "nonce": nonce,
        **fields,
    }


def pending_transaction(tx_id: str, sender: str, nonce: int, tx_hash: str) -> TransactionModel:
    return TransactionModel(
        id=tx_id,
        sender_address=sender,
        receiver_address="b" * 64,
        amount=1.0,
        fee=0.0,
        status=TransactionStatus.PENDING,
        timestamp=datetime(2026, 10, 20, 11, 0),
        signature="sig",
        tx_hash=tx_hash,
        nonce=nonce,
    )


@pytest.mark.asyncio
async def test_an_adopted_chain_keeps_payloads_and_nonces_and_takes_the_place_of_pending_copies(
    session: AsyncSession,
) -> None:
    session.add_all(
        [
            # The new chain mined this very transaction
            pending_transaction("our-copy", "alice", 1, tx_hash="hash-theirs"),
            # Another transaction with a nonce the new chain used
            pending_transaction("our-rival", "bob", 1, tx_hash="hash-rival"),
            # Still waiting to be mined
            pending_transaction("our-next", "alice", 2, tx_hash="hash-next"),
        ]
    )
    await session.flush()
    chain = [
        {
            "id": "block-1",
            "block_number": 1,
            "previous_hash": "0" * 64,
            "timestamp": "2026-10-20T12:00:00Z",
            "nonce": 42,
            "block_hash": "0000" + "a" * 60,
            "transactions": [
                peer_transaction("theirs", "alice", 1, payload="document-hash"),
                peer_transaction("bobs", "bob", 1),
            ],
        }
    ]

    await BlockRepositoryImpl(session).replace_chain(chain)

    session.expunge_all()
    rows = {tx.id: tx for tx in (await session.execute(select(TransactionModel))).scalars()}
    assert set(rows) == {"theirs", "bobs", "our-next"}
    assert (rows["theirs"].payload, rows["theirs"].nonce) == ("document-hash", 1)
