from abc import ABC, abstractmethod
from typing import Any


class PasswordHasher(ABC):
    @abstractmethod
    def hash_password(self, password: str) -> str:
        pass

    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        pass


class TokenService(ABC):
    @abstractmethod
    def create_access_token(self, subject: str, role: str) -> str:
        pass

    @abstractmethod
    def verify_token(self, token: str) -> dict[str, Any]:
        """Returns the token's claims; raises ValueError if the token is invalid or expired."""
        pass
