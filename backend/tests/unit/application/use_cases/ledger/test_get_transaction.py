from datetime import UTC, datetime
from typing import Any
from unittest.mock import create_autospec

import pytest

from backend.app.application.use_cases.ledger.get_transaction import GetTransactionByHashUseCase
from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository


@pytest.fixture
def mock_tx_repo() -> Any:
    return create_autospec(TransactionRepository, instance=True)


@pytest.fixture
def mock_block_repo() -> Any:
    return create_autospec(BlockRepository, instance=True)


def transaction(status: TransactionStatus, block_id: str | None) -> Transaction:
    return Transaction(
        id="1",
        sender_address="s",
        receiver_address="r",
        amount=10.0,
        fee=1.0,
        status=status,
        timestamp=datetime.now(UTC),
        signature="sig",
        tx_hash="hash",
        block_id=block_id,
    )


@pytest.mark.asyncio
async def test_a_pending_transaction_has_no_block(mock_tx_repo: Any, mock_block_repo: Any) -> None:
    use_case = GetTransactionByHashUseCase(mock_tx_repo, mock_block_repo)
    mock_tx_repo.get_by_hash.return_value = transaction(TransactionStatus.PENDING, block_id=None)

    result = await use_case.execute("hash")

    assert result is not None
    assert (result.tx_hash, result.block_number, result.block_hash) == ("hash", None, None)
    mock_block_repo.get_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_a_confirmed_transaction_carries_its_block(mock_tx_repo: Any, mock_block_repo: Any) -> None:
    use_case = GetTransactionByHashUseCase(mock_tx_repo, mock_block_repo)
    mock_tx_repo.get_by_hash.return_value = transaction(TransactionStatus.CONFIRMED, block_id="b1")
    mock_block_repo.get_by_id.return_value = Block(
        id="b1", block_number=3, previous_hash="prev", timestamp=datetime.now(UTC), block_hash="block_hash"
    )

    result = await use_case.execute("hash")

    assert result is not None
    assert (result.block_number, result.block_hash) == (3, "block_hash")
    mock_block_repo.get_by_id.assert_called_once_with("b1")


@pytest.mark.asyncio
async def test_get_transaction_not_found(mock_tx_repo: Any, mock_block_repo: Any) -> None:
    use_case = GetTransactionByHashUseCase(mock_tx_repo, mock_block_repo)
    mock_tx_repo.get_by_hash.return_value = None

    result = await use_case.execute("hash")

    assert result is None
    mock_tx_repo.get_by_hash.assert_called_once_with("hash")
