from datetime import datetime
from typing import Optional

from typing import List
from pydantic import BaseModel


class BlockResponseDTO(BaseModel):
    id: str
    block_number: int
    previous_hash: str
    timestamp: datetime
    nonce: int
    block_hash: str
    transaction_ids: list[str]

class PaginatedBlockResponseDTO(BaseModel):
    items: List[BlockResponseDTO]
    total: int
    page: int
    size: int
