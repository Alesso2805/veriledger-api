from abc import ABC, abstractmethod
from datetime import datetime

from backend.app.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        pass

    @abstractmethod
    async def set_password_hash(self, user_id: str, password_hash: str) -> None:
        """Replaces the user's password hash, as rotating the admin's password does (VLA-28)."""

    @abstractmethod
    async def active_demo_accounts(self, now: datetime) -> tuple[int, datetime | None]:
        """How many demo accounts have not expired by now, and when the first of them expires."""

    @abstractmethod
    async def delete_expired(self, now: datetime) -> int:
        """Deletes the demo accounts that expired before now and returns how many."""
