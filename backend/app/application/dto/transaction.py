from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.domain.entities.transaction import TransactionStatus


class TransactionCreateRequestDTO(BaseModel):
    sender_address: str
    receiver_address: str
    amount: float = Field(..., ge=0)
    fee: float = Field(default=0.0, ge=0)
    signature: str
    payload: str | None = None


class TransactionResponseDTO(BaseModel):
    id: str
    sender_address: str
    receiver_address: str
    amount: float
    fee: float
    status: TransactionStatus
    timestamp: datetime
    signature: str
    tx_hash: str | None = None
    payload: str | None = None
    block_id: str | None = None
