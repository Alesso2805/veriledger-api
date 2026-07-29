import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import String

from backend.app.infrastructure.models.base_model import BaseModel

class NodeModel(BaseModel):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    url: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
