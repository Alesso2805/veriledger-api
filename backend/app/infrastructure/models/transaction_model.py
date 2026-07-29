import uuid
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from backend.app.domain.entities.transaction import TransactionStatus
from backend.app.infrastructure.models.base_model import BaseModel
from backend.app.infrastructure.models.block_model import BlockModel


class TransactionModel(BaseModel):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_address: Mapped[str] = mapped_column(String, index=True)
    receiver_address: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 8))
    status: Mapped[TransactionStatus] = mapped_column(SAEnum(TransactionStatus), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tx_hash: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    
    block_id: Mapped[Optional[str]] = mapped_column(ForeignKey("blocks.id"), nullable=True)
    block = relationship("BlockModel", back_populates="transactions")
