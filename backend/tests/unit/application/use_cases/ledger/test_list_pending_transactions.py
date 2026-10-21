from datetime import UTC, datetime
from typing import Any
from unittest.mock import create_autospec

import pytest

from backend.app.application.use_cases.ledger.list_pending_transactions import ListPendingTransactionsUseCase
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository


@pytest.fixture
def mock_tx_repo() -> Any:
    return create_autospec(TransactionRepository, instance=True)


def pending(tx_hash: str) -> Transaction:
    return Transaction(
        id=tx_hash,
        sender_address="s",
        receiver_address="r",
        amount=1.0,
        fee=0.0,
        status=TransactionStatus.PENDING,
        timestamp=datetime.now(UTC),
        signature="sig",
        tx_hash=tx_hash,
        payload="doc" if tx_hash == "b" else None,
    )


@pytest.mark.asyncio
async def test_a_page_of_pending_transactions_with_the_real_total(mock_tx_repo: Any) -> None:
    use_case = ListPendingTransactionsUseCase(mock_tx_repo)
    mock_tx_repo.list_by_status.return_value = [pending("a"), pending("b")]
    mock_tx_repo.count_by_status.return_value = 5

    result = await use_case.execute(skip=2, limit=2)

    assert [(item.tx_hash, item.payload) for item in result.items] == [("a", None), ("b", "doc")]
    assert (result.total, result.page, result.size) == (5, 2, 2)
    assert all(item.block_number is None and item.block_hash is None for item in result.items)
    mock_tx_repo.list_by_status.assert_called_once_with(TransactionStatus.PENDING, 2, 2)
    mock_tx_repo.count_by_status.assert_called_once_with(TransactionStatus.PENDING)
