from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from backend.app.domain.chain_validator import GENESIS_PREVIOUS_HASH, ChainValidator
from backend.app.domain.entities.block import Block
from backend.app.infrastructure.security.sha256_hasher import SHA256HasherImpl

DIFFICULTY = 2
hasher = SHA256HasherImpl()
validator = ChainValidator(hasher, difficulty=DIFFICULTY)


def seal(block: dict[str, Any], difficulty: int = DIFFICULTY) -> dict[str, Any]:
    """Finds the block's nonce and hash, as a miner would, and returns it."""
    entity = Block(
        id=block["id"],
        block_number=block["block_number"],
        previous_hash=block["previous_hash"],
        timestamp=datetime.fromisoformat(block["timestamp"]),
        transaction_ids=[transaction["id"] for transaction in block["transactions"]],
    )
    while not (block_hash := hasher.hash_block(entity)).startswith("0" * difficulty):
        entity.nonce += 1
    return {**block, "nonce": entity.nonce, "block_hash": block_hash}


def mined_chain(length: int = 3) -> list[dict[str, Any]]:
    """A valid chain as /blocks/full serves it: newest first, timestamps in UTC written with "Z"."""
    blocks: list[dict[str, Any]] = []
    start = datetime(2026, 10, 21, 12, 0, 0, 123456, tzinfo=UTC)
    for number in range(length):
        block = {
            "id": f"block-{number}",
            "block_number": number,
            "previous_hash": blocks[-1]["block_hash"] if blocks else GENESIS_PREVIOUS_HASH,
            "timestamp": (start + timedelta(minutes=number)).isoformat().replace("+00:00", "Z"),
            "transactions": [{"id": f"coinbase-{number}"}, {"id": f"transfer-{number}"}],
        }
        blocks.append(seal(block))
    return list(reversed(blocks))


def oldest_first(chain: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(reversed(chain))


def test_a_mined_chain_keeps_every_rule() -> None:
    assert validator.violation(mined_chain()) is None


def test_an_empty_chain_is_refused() -> None:
    assert validator.violation([]) == "the chain is empty"


def test_a_chain_that_does_not_start_at_genesis_is_refused() -> None:
    blocks = oldest_first(mined_chain())
    blocks[0] = seal({**blocks[0], "previous_hash": "1" * 64})

    assert validator.violation(list(reversed(blocks))) == "the chain does not start at a genesis block"


def test_a_chain_with_a_missing_block_is_refused() -> None:
    blocks = oldest_first(mined_chain(4))
    del blocks[2]

    assert validator.violation(list(reversed(blocks))) == "block numbers are not consecutive: block 3 where 2 belongs"


def test_a_block_that_points_elsewhere_is_refused_even_with_a_valid_hash() -> None:
    blocks = oldest_first(mined_chain())
    # Re-sealed, so its own hash and difficulty hold and only the link breaks
    blocks[1] = seal({**blocks[1], "previous_hash": "0" * 4 + "f" * 60})

    assert validator.violation(list(reversed(blocks))) == "block 1 does not point at block 0"


def test_a_block_whose_contents_changed_is_refused() -> None:
    blocks = oldest_first(mined_chain())
    tampered = deepcopy(blocks[2])
    tampered["transactions"][1]["id"] = "a-transfer-that-was-never-mined"
    blocks[2] = tampered

    assert validator.violation(list(reversed(blocks))) == "block 2's hash does not match its contents"


def test_a_block_below_the_difficulty_is_refused() -> None:
    blocks = oldest_first(mined_chain())
    # A real hash of the block, found with less work than this node asks for
    easy = seal({**blocks[2]}, difficulty=0)
    if easy["block_hash"].startswith("0" * DIFFICULTY):
        easy = seal({**blocks[2], "timestamp": "2026-10-21T13:00:00Z"}, difficulty=0)
    blocks[2] = easy

    assert validator.violation(list(reversed(blocks))) == "block 2 does not meet the difficulty"


@pytest.mark.parametrize("field", ["id", "timestamp", "transactions", "block_hash"])
def test_a_malformed_block_is_refused(field: str) -> None:
    blocks = oldest_first(mined_chain())
    del blocks[1][field]

    assert validator.violation(list(reversed(blocks))) == "a block is malformed"
