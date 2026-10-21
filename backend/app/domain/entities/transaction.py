from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TransactionStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


@dataclass
class Transaction:
    id: str
    sender_address: str
    receiver_address: str
    amount: float
    fee: float
    status: TransactionStatus
    timestamp: datetime
    signature: str = ""
    tx_hash: str | None = None
    payload: str | None = None
    nonce: int | None = None
    block_id: str | None = None
