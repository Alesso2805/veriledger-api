from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.app.domain.entities.transaction import TransactionStatus


class TransactionCreateRequestDTO(BaseModel):
    sender_address: str
    receiver_address: str
    amount: float = Field(..., gt=0)
    fee: float = Field(default=0.0, ge=0)
    signature: str


class TransactionResponseDTO(BaseModel):
    id: str
    sender_address: str
    receiver_address: str
    amount: float
    fee: float
    status: TransactionStatus
    timestamp: datetime
    signature: str
    tx_hash: Optional[str] = None
    block_id: Optional[str] = None
