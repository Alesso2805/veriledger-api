import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain.entities.transaction import TransactionStatus
from backend.app.infrastructure.models.base_model import BaseModel


class BlockModel(BaseModel):
    __tablename__ = "blocks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    block_number: Mapped[int] = mapped_column(unique=True, index=True)
    previous_hash: Mapped[str] = mapped_column(String)
    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    block_hash: Mapped[str] = mapped_column(String, unique=True, index=True)

    transactions = relationship("TransactionModel", back_populates="block")
