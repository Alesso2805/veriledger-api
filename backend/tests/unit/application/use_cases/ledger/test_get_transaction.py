from datetime import UTC, datetime
from typing import Any
from unittest.mock import create_autospec

import pytest

from backend.app.application.use_cases.ledger.get_transaction import GetTransactionByHashUseCase
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository


@pytest.fixture
def mock_tx_repo() -> Any:
    return create_autospec(TransactionRepository, instance=True)


@pytest.mark.asyncio
async def test_get_transaction_success(mock_tx_repo: Any) -> None:
    use_case = GetTransactionByHashUseCase(mock_tx_repo)

    expected_tx = Transaction(
        id="1",
        sender_address="s",
        receiver_address="r",
        amount=10.0,
        fee=1.0,
        status=TransactionStatus.PENDING,
        timestamp=datetime.now(UTC),
        signature="sig",
        tx_hash="hash",
    )
    mock_tx_repo.get_by_hash.return_value = expected_tx

    result = await use_case.execute("hash")

    assert result == expected_tx
    mock_tx_repo.get_by_hash.assert_called_once_with("hash")


@pytest.mark.asyncio
async def test_get_transaction_not_found(mock_tx_repo: Any) -> None:
    use_case = GetTransactionByHashUseCase(mock_tx_repo)

    mock_tx_repo.get_by_hash.return_value = None

    result = await use_case.execute("hash")

    assert result is None
    mock_tx_repo.get_by_hash.assert_called_once_with("hash")
