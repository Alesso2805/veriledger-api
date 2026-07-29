from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
