from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


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
    tx_hash: Optional[str] = None
    payload: Optional[str] = None
    block_id: Optional[str] = None
