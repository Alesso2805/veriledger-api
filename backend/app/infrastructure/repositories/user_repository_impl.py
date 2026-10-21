from datetime import datetime
from typing import Any, cast

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.entities.user import User
from backend.app.domain.ports.repositories.user_repository import UserRepository
from backend.app.infrastructure.models.user import UserModel


class UserRepositoryImpl(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: str) -> User | None:
        stmt = select(UserModel).where(UserModel.id == user_id, UserModel.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email, UserModel.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def save(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
            expires_at=user.expires_at,
        )
        self.session.add(model)
        await self.session.flush()
        return model.to_entity()

    async def delete_expired(self, now: datetime) -> int:
        # Only the accounts: blocks and transactions refer to addresses, never to users, so the chain keeps them
        result = await self.session.execute(delete(UserModel).where(UserModel.expires_at < now))
        return cast(CursorResult[Any], result).rowcount
