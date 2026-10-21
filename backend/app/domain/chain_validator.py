from datetime import datetime
from typing import Any

from backend.app.domain.entities.block import Block
from backend.app.domain.ports.services.hashing import HasherService

GENESIS_PREVIOUS_HASH = "0" * 64


class ChainValidator:
    """SPEC › Valid chain: whether a peer's chain, as /blocks/full serves it, may replace ours (VLA-18)."""

    def __init__(self, hasher: HasherService, difficulty: int):
        self._hasher = hasher
        self._target = "0" * difficulty

    def violation(self, chain: list[dict[str, Any]]) -> str | None:
        """The first rule the chain breaks, in words, or None when it keeps them all."""
        if not chain:
            return "the chain is empty"
        # /blocks/full lists the newest block first; the rules read from the genesis up
        blocks = list(reversed(chain))
        try:
            for number, block in enumerate(blocks):
                reason = self._block_violation(block, blocks[number - 1] if number else None, number)
                if reason:
                    return reason
        except (KeyError, TypeError, ValueError):
            return "a block is malformed"
        return None

    def _block_violation(self, block: dict[str, Any], previous: dict[str, Any] | None, number: int) -> str | None:
        if block["block_number"] != number:
            return f"block numbers are not consecutive: block {block['block_number']} where {number} belongs"
        if previous is None and block["previous_hash"] != GENESIS_PREVIOUS_HASH:
            return "the chain does not start at a genesis block"
        if previous is not None and block["previous_hash"] != previous["block_hash"]:
            return f"block {number} does not point at block {number - 1}"
        recomputed = self._hasher.hash_block(
            Block(
                id=block["id"],
                block_number=number,
                previous_hash=block["previous_hash"],
                # Pydantic writes UTC as "Z"; read back, it hashes as the miner's "+00:00" did
                timestamp=datetime.fromisoformat(block["timestamp"]),
                nonce=block["nonce"],
                transaction_ids=[transaction["id"] for transaction in block["transactions"]],
            )
        )
        if block["block_hash"] != recomputed:
            return f"block {number}'s hash does not match its contents"
        if not recomputed.startswith(self._target):
            return f"block {number} does not meet the difficulty"
        return None
