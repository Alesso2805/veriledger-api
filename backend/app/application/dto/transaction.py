from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field

from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
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
    # Null while the transaction waits in the mempool
    block_number: int | None = None
    block_hash: str | None = None

    @classmethod
    def from_entity(cls, transaction: Transaction, block: Block | None = None) -> Self:
        return cls(
            id=transaction.id,
            sender_address=transaction.sender_address,
            receiver_address=transaction.receiver_address,
            amount=transaction.amount,
            fee=transaction.fee,
            status=transaction.status,
            timestamp=transaction.timestamp,
            signature=transaction.signature,
            tx_hash=transaction.tx_hash,
            payload=transaction.payload,
            block_id=transaction.block_id,
            block_number=block.block_number if block else None,
            block_hash=block.block_hash if block else None,
        )
