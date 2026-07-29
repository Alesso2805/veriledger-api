import pytest
from datetime import datetime, timezone
from unittest.mock import create_autospec, AsyncMock

from backend.app.application.use_cases.auth.login import LoginUseCase
from backend.app.application.dto.user import LoginDTO
from backend.app.domain.entities.user import User, UserRole
from backend.app.domain.ports.repositories.user_repository import UserRepository
from backend.app.domain.ports.services.security import PasswordHasher, TokenService

@pytest.fixture
def mock_user_repo():
    return create_autospec(UserRepository, instance=True)

@pytest.fixture
def mock_password_hasher():
    return create_autospec(PasswordHasher, instance=True)

@pytest.fixture
def mock_token_service():
    return create_autospec(TokenService, instance=True)

@pytest.mark.asyncio
async def test_login_success(mock_user_repo, mock_password_hasher, mock_token_service):
    use_case = LoginUseCase(mock_user_repo, mock_password_hasher, mock_token_service)
    
    now = datetime.now(timezone.utc)
    mock_user = User(id="1", email="test@test.com", password_hash="hash", role=UserRole.ADMIN, created_at=now, updated_at=now)
    mock_user_repo.get_by_email.return_value = mock_user
    mock_password_hasher.verify_password.return_value = True
    mock_token_service.create_access_token.return_value = "fake_token"
    
    request = LoginDTO(email="test@test.com", password="password123")
    result = await use_case.execute(request)
    
    assert result.access_token == "fake_token"
    mock_user_repo.get_by_email.assert_called_once_with("test@test.com")
    mock_password_hasher.verify_password.assert_called_once_with("password123", "hash")
    mock_token_service.create_access_token.assert_called_once_with(subject="1", role=UserRole.ADMIN.value)

@pytest.mark.asyncio
async def test_login_invalid_email(mock_user_repo, mock_password_hasher, mock_token_service):
    use_case = LoginUseCase(mock_user_repo, mock_password_hasher, mock_token_service)
    
    mock_user_repo.get_by_email.return_value = None
    
    request = LoginDTO(email="wrong@test.com", password="password123")
    
    with pytest.raises(ValueError, match="Invalid credentials"):
        await use_case.execute(request)

@pytest.mark.asyncio
async def test_login_invalid_password(mock_user_repo, mock_password_hasher, mock_token_service):
    use_case = LoginUseCase(mock_user_repo, mock_password_hasher, mock_token_service)
    
    now = datetime.now(timezone.utc)
    mock_user = User(id="1", email="test@test.com", password_hash="hash", role=UserRole.ADMIN, created_at=now, updated_at=now)
    mock_user_repo.get_by_email.return_value = mock_user
    mock_password_hasher.verify_password.return_value = False
    
    request = LoginDTO(email="test@test.com", password="wrongpassword")
    
    with pytest.raises(ValueError, match="Invalid credentials"):
        await use_case.execute(request)
