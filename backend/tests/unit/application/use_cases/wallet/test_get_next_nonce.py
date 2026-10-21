from typing import Any
from unittest.mock import create_autospec

import pytest

from backend.app.application.use_cases.wallet.get_next_nonce import GetNextNonceUseCase
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository


@pytest.fixture
def mock_tx_repo() -> Any:
    return create_autospec(TransactionRepository, instance=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(("last_nonce", "expected"), [(None, 1), (1, 2), (9, 10)])
async def test_the_next_nonce_is_one_more_than_the_last(
    mock_tx_repo: Any, last_nonce: int | None, expected: int
) -> None:
    mock_tx_repo.get_last_nonce.return_value = last_nonce

    assert await GetNextNonceUseCase(mock_tx_repo).execute("address") == expected
    mock_tx_repo.get_last_nonce.assert_called_once_with("address")
