from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Block:
    id: str
    block_number: int
    previous_hash: str
    timestamp: datetime
    nonce: int = 0
    block_hash: Optional[str] = None
    transaction_ids: list[str] = field(default_factory=list)
