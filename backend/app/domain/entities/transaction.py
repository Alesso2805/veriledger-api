from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TransactionStatus(str, Enum):
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
    block_id: str | None = None
