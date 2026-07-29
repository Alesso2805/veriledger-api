from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BlockResponseDTO(BaseModel):
    id: str
    block_number: int
    previous_hash: str
    timestamp: datetime
    block_hash: Optional[str] = None
    transaction_ids: list[str]
