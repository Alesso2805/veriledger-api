import pytest
from datetime import datetime, timezone
from unittest.mock import create_autospec

from backend.app.application.use_cases.auth.register_user import RegisterUserUseCase
from backend.app.application.dto.user import UserCreateDTO
from backend.app.domain.entities.user import User, UserRole
from backend.app.domain.ports.repositories.user_repository import UserRepository
from backend.app.domain.ports.services.security import PasswordHasher

@pytest.fixture
def mock_user_repo():
    return create_autospec(UserRepository, instance=True)

@pytest.fixture
def mock_password_hasher():
    hasher = create_autospec(PasswordHasher, instance=True)
    hasher.hash_password.return_value = "hashed_password"
    return hasher

@pytest.mark.asyncio
async def test_register_user_success(mock_user_repo, mock_password_hasher):
    use_case = RegisterUserUseCase(mock_user_repo, mock_password_hasher)
    
    request = UserCreateDTO(email="new@test.com", password="password123", role=UserRole.VIEWER)
    mock_user_repo.get_by_email.return_value = None
    
    async def mock_save(user):
        return user
    mock_user_repo.save.side_effect = mock_save
    
    result = await use_case.execute(request)
    
    assert result.email == "new@test.com"
    assert result.role == UserRole.VIEWER
    mock_user_repo.get_by_email.assert_called_once_with("new@test.com")
    mock_password_hasher.hash_password.assert_called_once_with("password123")
    mock_user_repo.save.assert_called_once()

@pytest.mark.asyncio
async def test_register_user_already_exists(mock_user_repo, mock_password_hasher):
    use_case = RegisterUserUseCase(mock_user_repo, mock_password_hasher)
    
    request = UserCreateDTO(email="existing@test.com", password="password123", role=UserRole.VIEWER)
    
    now = datetime.now(timezone.utc)
    existing = User(id="1", email="existing@test.com", password_hash="hash", role=UserRole.VIEWER, created_at=now, updated_at=now)
    mock_user_repo.get_by_email.return_value = existing
    
    with pytest.raises(ValueError, match="Email already registered"):
        await use_case.execute(request)
