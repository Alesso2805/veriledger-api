from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Block:
    id: str
    block_number: int
    previous_hash: str
    timestamp: datetime
    nonce: int = 0
    block_hash: str | None = None
    transaction_ids: list[str] = field(default_factory=list)
    transaction_hashes: list[str] = field(default_factory=list)
