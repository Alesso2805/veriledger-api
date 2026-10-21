from datetime import UTC, datetime
from typing import Any
from unittest.mock import create_autospec

import pytest

from backend.app.application.use_cases.wallet.list_address_transactions import ListAddressTransactionsUseCase
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


def transaction(tx_hash: str, block_id: str | None) -> Transaction:
    return Transaction(
        id=tx_hash,
        sender_address="alice",
        receiver_address="bob",
        amount=1.0,
        fee=0.0,
        status=TransactionStatus.CONFIRMED if block_id else TransactionStatus.PENDING,
        timestamp=datetime.now(UTC),
        signature="sig",
        tx_hash=tx_hash,
        block_id=block_id,
    )


def block(block_id: str, number: int) -> Block:
    return Block(
        id=block_id, block_number=number, previous_hash="p", timestamp=datetime.now(UTC), block_hash=f"h{number}"
    )


@pytest.mark.asyncio
async def test_each_transaction_carries_its_block_read_in_one_query(mock_tx_repo: Any, mock_block_repo: Any) -> None:
    mock_tx_repo.list_by_address.return_value = [
        transaction("pending", None),
        transaction("a", "b2"),
        transaction("b", "b1"),
        transaction("c", "b2"),
    ]
    mock_tx_repo.count_by_address.return_value = 9
    mock_block_repo.get_by_ids.return_value = [block("b1", 1), block("b2", 2)]

    result = await ListAddressTransactionsUseCase(mock_tx_repo, mock_block_repo).execute("alice", skip=4, limit=4)

    assert [(item.tx_hash, item.block_number, item.block_hash) for item in result.items] == [
        ("pending", None, None),
        ("a", 2, "h2"),
        ("b", 1, "h1"),
        ("c", 2, "h2"),
    ]
    assert (result.total, result.page, result.size) == (9, 2, 4)
    mock_tx_repo.list_by_address.assert_called_once_with("alice", 4, 4)
    mock_block_repo.get_by_ids.assert_called_once_with(["b1", "b2"])


@pytest.mark.asyncio
async def test_a_page_with_no_confirmed_transaction_reads_no_block(mock_tx_repo: Any, mock_block_repo: Any) -> None:
    mock_tx_repo.list_by_address.return_value = [transaction("pending", None)]
    mock_tx_repo.count_by_address.return_value = 1

    result = await ListAddressTransactionsUseCase(mock_tx_repo, mock_block_repo).execute("alice", skip=0, limit=10)

    assert [item.tx_hash for item in result.items] == ["pending"]
    mock_block_repo.get_by_ids.assert_not_called()
