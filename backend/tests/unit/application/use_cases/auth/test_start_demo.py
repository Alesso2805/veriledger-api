from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import create_autospec

import pytest

from backend.app.application.use_cases.auth.start_demo import StartDemoUseCase
from backend.app.domain.entities.user import User, UserRole
from backend.app.domain.ports.repositories.user_repository import UserRepository
from backend.app.domain.ports.services.security import TokenService


@pytest.mark.asyncio
async def test_a_demo_is_a_trader_without_email_for_24_hours_whose_token_ends_with_it() -> None:
    user_repo: Any = create_autospec(UserRepository, instance=True)
    token_service: Any = create_autospec(TokenService, instance=True)
    user_repo.save.side_effect = lambda user: user
    token_service.create_access_token.return_value = "demo-token"
    before = datetime.now(UTC)

    result = await StartDemoUseCase(user_repo, token_service).execute()

    saved: User = user_repo.save.call_args.args[0]
    assert (saved.role, saved.email, saved.password_hash) == (UserRole.TRADER, None, None)
    assert saved.expires_at is not None
    assert before + timedelta(hours=24) <= saved.expires_at <= datetime.now(UTC) + timedelta(hours=24)
    assert saved.display_name.startswith("Guest ")
    token_service.create_access_token.assert_called_once_with(
        subject=saved.id, role="trader", expires_at=saved.expires_at, demo=True
    )
    assert result.access_token == "demo-token"
