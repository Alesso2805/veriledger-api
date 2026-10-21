import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain.entities.transaction import TransactionStatus
from backend.app.infrastructure.models.base_model import BaseModel


class TransactionModel(BaseModel):
    __tablename__ = "transactions"
    # A sender uses each nonce once (ADR-0004); rows from before VLA-16 have none, and NULLs never collide
    __table_args__ = (
        UniqueConstraint("sender_address", "nonce", name="uq_transactions_sender_nonce"),
        # The database refuses what the use cases already refuse, whoever writes the row (VLA-25)
        CheckConstraint("amount >= 0", name="ck_transactions_amount_not_negative"),
        CheckConstraint("fee >= 0", name="ck_transactions_fee_not_negative"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_address: Mapped[str] = mapped_column(String, index=True)
    receiver_address: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 8))
    fee: Mapped[float] = mapped_column(Numeric(18, 8), default=0.0, server_default="0.0")
    status: Mapped[TransactionStatus] = mapped_column(SAEnum(TransactionStatus), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    signature: Mapped[str] = mapped_column(String)
    tx_hash: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    payload: Mapped[str | None] = mapped_column(String, nullable=True)
    nonce: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    block_id: Mapped[str | None] = mapped_column(ForeignKey("blocks.id"), nullable=True)
    block = relationship("BlockModel", back_populates="transactions")
