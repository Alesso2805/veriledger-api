from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, create_autospec, patch

import pytest

from backend.app.application.use_cases.ledger.mine_block import MineBlockUseCase
from backend.app.domain.entities.block import Block
from backend.app.domain.entities.node import Node
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.services.consensus import ConsensusService
from backend.app.domain.ports.services.hashing import HasherService


@pytest.fixture
def mock_block_repo() -> Any:
    return create_autospec(BlockRepository, instance=True)


@pytest.fixture
def mock_tx_repo() -> Any:
    return create_autospec(TransactionRepository, instance=True)


@pytest.fixture
def mock_consensus() -> Any:
    c = create_autospec(ConsensusService, instance=True)
    c.mine_block.return_value = (123, "new_block_hash")
    return c


@pytest.fixture
def mock_hasher() -> Any:
    h = create_autospec(HasherService, instance=True)
    h.hash_transaction.return_value = "coinbase_tx_hash"
    return h


@pytest.fixture
def mock_node_repo() -> Any:
    return create_autospec(NodeRepository, instance=True)


@pytest.mark.asyncio
async def test_mine_block_success(
    mock_block_repo: Any, mock_tx_repo: Any, mock_consensus: Any, mock_hasher: Any, mock_node_repo: Any
) -> None:
    use_case = MineBlockUseCase(mock_block_repo, mock_tx_repo, mock_consensus, mock_hasher, mock_node_repo)

    pending_tx = Transaction(
        id="tx1",
        sender_address="s",
        receiver_address="r",
        amount=10.0,
        fee=2.0,
        status=TransactionStatus.PENDING,
        timestamp=datetime.now(UTC),
        signature="sig",
        tx_hash="pending_tx_hash",
    )
    mock_tx_repo.get_by_status.return_value = [pending_tx]

    last_block = Block(id="b1", block_number=5, previous_hash="prev", timestamp=datetime.now(UTC), transaction_ids=[])
    last_block.block_hash = "last_hash"
    mock_block_repo.get_latest_block.return_value = last_block

    mock_node_repo.get_all.return_value = [Node(id="1", url="http://peer", status="ACTIVE")]

    result = await use_case.execute("miner1")

    assert result.block_number == 6
    assert result.previous_hash == "last_hash"
    assert result.nonce == 123
    assert result.block_hash == "new_block_hash"
    assert len(result.transaction_ids) == 2  # 1 coinbase + 1 pending
    assert result.transaction_hashes == ["coinbase_tx_hash", "pending_tx_hash"]
    mock_tx_repo.create.assert_called_once()
    assert mock_tx_repo.create.call_args.args[0].nonce == 6  # the coinbase's nonce is its block number
    mock_block_repo.create.assert_called_once()

    # The router asks peers to resolve after the response; execute only reads them while the session is open
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        await use_case.broadcast_block()
    mock_post.assert_awaited_once_with("http://peer/nodes/resolve")
