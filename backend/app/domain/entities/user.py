from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


@dataclass
class User:
    id: str
    # A demo account (ADR-0006) has neither
    email: str | None
    password_hash: str | None
    role: UserRole
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    expires_at: datetime | None = None

    @property
    def is_demo(self) -> bool:
        return self.expires_at is not None

    @property
    def display_name(self) -> str:
        # A demo account is named after its id, so the name needs no column of its own
        return self.email if self.email is not None else f"Guest {self.id[-4:].upper()}"

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at
