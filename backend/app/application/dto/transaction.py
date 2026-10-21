from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.domain.entities.transaction import TransactionStatus
from backend.app.domain.signed_message import AMOUNT


class TransactionCreateRequestDTO(BaseModel):
    sender_address: str
    receiver_address: str
    # The same 8-decimal strings that were signed (ADR-0004), so neither side formats a float
    amount: str = Field(..., pattern=AMOUNT.pattern, examples=["10.00000000"])
    fee: str = Field(default="0.00000000", pattern=AMOUNT.pattern, examples=["0.10000000"])
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
