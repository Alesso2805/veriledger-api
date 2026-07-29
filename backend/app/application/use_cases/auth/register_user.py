import uuid
from datetime import UTC, datetime

from backend.app.application.dto.user import UserCreateDTO, UserResponseDTO
from backend.app.domain.entities.user import User
from backend.app.domain.ports.repositories.user_repository import UserRepository
from backend.app.domain.ports.services.security import PasswordHasher


class RegisterUserUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        password_hasher: PasswordHasher,
    ):
        self.user_repo = user_repo
        self.password_hasher = password_hasher

    async def execute(self, data: UserCreateDTO) -> UserResponseDTO:
        existing_user = await self.user_repo.get_by_email(data.email)
        if existing_user:
            raise ValueError("Email already registered")

        hashed_password = self.password_hasher.hash_password(data.password)
        now = datetime.now(UTC)

        user = User(
            id=str(uuid.uuid4()),
            email=data.email,
            password_hash=hashed_password,
            role=data.role,
            created_at=now,
            updated_at=now,
        )

        saved_user = await self.user_repo.save(user)

        return UserResponseDTO(
            id=saved_user.id,
            email=saved_user.email,
            role=saved_user.role,
            created_at=saved_user.created_at,
            updated_at=saved_user.updated_at,
        )
