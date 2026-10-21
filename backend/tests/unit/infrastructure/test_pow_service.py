import threading
from datetime import UTC, datetime

import pytest

from backend.app.domain.entities.block import Block
from backend.app.infrastructure.consensus.pow_service import ProofOfWorkServiceImpl
from backend.app.infrastructure.security.sha256_hasher import SHA256HasherImpl


def block() -> Block:
    return Block(
        id="b",
        block_number=1,
        previous_hash="0" * 64,
        timestamp=datetime(2026, 10, 21, tzinfo=UTC),
        transaction_ids=["t"],
    )


@pytest.mark.asyncio
async def test_the_nonce_found_gives_a_hash_with_as_many_leading_zeros_as_the_difficulty() -> None:
    hasher = SHA256HasherImpl()
    mined = block()

    nonce, block_hash = await ProofOfWorkServiceImpl(hasher).mine_block(mined, difficulty=2)

    assert block_hash.startswith("00")
    assert (mined.nonce, hasher.hash_block(mined)) == (nonce, block_hash)


@pytest.mark.asyncio
async def test_the_search_runs_in_a_worker_thread_not_on_the_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    hasher = SHA256HasherImpl()
    threads: set[int] = set()
    hash_block = hasher.hash_block

    def recording(mined: Block) -> str:
        threads.add(threading.get_ident())
        return hash_block(mined)

    monkeypatch.setattr(hasher, "hash_block", recording)

    await ProofOfWorkServiceImpl(hasher).mine_block(block(), difficulty=1)

    assert threads and threading.get_ident() not in threads
