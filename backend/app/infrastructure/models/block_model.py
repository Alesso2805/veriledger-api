import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain.entities.transaction import TransactionStatus
from backend.app.infrastructure.models.base_model import BaseModel


class BlockModel(BaseModel):
    __tablename__ = "blocks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    block_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    previous_hash: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    nonce: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    block_hash: Mapped[str] = mapped_column(String, unique=True, index=True)

    transactions = relationship("TransactionModel", back_populates="block")
