from datetime import UTC, datetime
from typing import Any
from unittest.mock import create_autospec

import pytest

from backend.app.application.use_cases.auth.purge_expired_demo_accounts import PurgeExpiredDemoAccountsUseCase
from backend.app.domain.ports.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_the_demo_accounts_expired_by_now_are_deleted() -> None:
    user_repo: Any = create_autospec(UserRepository, instance=True)
    user_repo.delete_expired.return_value = 3
    before = datetime.now(UTC)

    assert await PurgeExpiredDemoAccountsUseCase(user_repo).execute() == 3

    (now,) = user_repo.delete_expired.call_args.args
    assert before <= now <= datetime.now(UTC)
