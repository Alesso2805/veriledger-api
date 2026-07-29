from backend.app.application.dto.user import LoginDTO, TokenDTO
from backend.app.domain.ports.repositories.user_repository import UserRepository
from backend.app.domain.ports.services.security import PasswordHasher, TokenService


class LoginUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ):
        self.user_repo = user_repo
        self.password_hasher = password_hasher
        self.token_service = token_service

    async def execute(self, data: LoginDTO) -> TokenDTO:
        user = await self.user_repo.get_by_email(data.email)
        if not user:
            raise ValueError("Invalid credentials")

        if not self.password_hasher.verify_password(data.password, user.password_hash):
            raise ValueError("Invalid credentials")

        token = self.token_service.create_access_token(subject=user.id, role=user.role.value)
        return TokenDTO(access_token=token)
