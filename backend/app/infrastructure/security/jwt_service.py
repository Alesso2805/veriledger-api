from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from backend.app.core.config import settings
from backend.app.domain.ports.services.security import TokenService


class JWTTokenService(TokenService):
    def create_access_token(self, subject: str, role: str) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode = {"exp": expire, "sub": str(subject), "role": role}
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            return payload
        except jwt.PyJWTError as e:
            raise ValueError(f"Invalid token: {e}") from e
