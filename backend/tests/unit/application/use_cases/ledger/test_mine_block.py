from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from unittest.mock import create_autospec

import pytest

from backend.app.application.use_cases.ledger.mine_block import MineBlockUseCase
from backend.app.domain.entities.block import Block
from backend.app.domain.entities.node import Node
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.errors import BlockHeightTakenError
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.services.consensus import ConsensusService
from backend.app.domain.ports.services.hashing import HasherService
from backend.app.domain.ports.services.peer_client import PeerClient

DEFAULTS: dict[str, Any] = {"difficulty": 4, "reward": 50.0}


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


@pytest.fixture
def mock_peer_client() -> Any:
    return create_autospec(PeerClient, instance=True)


@pytest.mark.asyncio
async def test_mine_block_success(
    mock_block_repo: Any,
    mock_tx_repo: Any,
    mock_consensus: Any,
    mock_hasher: Any,
    mock_node_repo: Any,
    mock_peer_client: Any,
) -> None:
    use_case = MineBlockUseCase(
        mock_block_repo,
        mock_tx_repo,
        mock_consensus,
        mock_hasher,
        mock_node_repo,
        mock_peer_client,
        difficulty=4,
        reward=50.0,
    )

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
    await use_case.broadcast_block()
    mock_peer_client.request_resolve.assert_awaited_once_with(["http://peer"])


def step(order: list[str], name: str, result: Callable[..., Any]) -> Callable[..., Any]:
    def record(*args: Any, **kwargs: Any) -> Any:
        order.append(name)
        return result(*args, **kwargs)

    return record


def pending_transaction() -> Transaction:
    return Transaction(
        id="tx1",
        sender_address="s",
        receiver_address="r",
        amount=10.0,
        fee=0.0,
        status=TransactionStatus.PENDING,
        timestamp=datetime.now(UTC),
        signature="sig",
        tx_hash="pending_tx_hash",
    )


@pytest.mark.asyncio
async def test_nothing_is_written_until_the_nonce_is_found_and_the_block_goes_first(
    mock_block_repo: Any, mock_tx_repo: Any, mock_consensus: Any, mock_hasher: Any
) -> None:
    order: list[str] = []
    mock_block_repo.get_latest_block.side_effect = step(order, "latest block", lambda: None)
    mock_tx_repo.get_by_status.side_effect = step(order, "mempool", lambda status: [pending_transaction()])
    mock_consensus.mine_block.side_effect = step(order, "proof of work", lambda block, difficulty: (123, "h"))
    mock_block_repo.create.side_effect = step(order, "block", lambda block: block)
    mock_tx_repo.create.side_effect = step(order, "coinbase", lambda tx: tx)
    mock_tx_repo.update.side_effect = step(order, "confirmation", lambda tx: tx)

    result = await MineBlockUseCase(mock_block_repo, mock_tx_repo, mock_consensus, mock_hasher, **DEFAULTS).execute(
        "miner1"
    )

    assert order == ["latest block", "mempool", "proof of work", "block", "coinbase", "confirmation"]
    # The coinbase is written once, already in its block
    assert mock_tx_repo.create.call_args.args[0].block_id == result.id


@pytest.mark.asyncio
async def test_a_taken_height_stops_the_block_before_the_coinbase_and_the_confirmations(
    mock_block_repo: Any, mock_tx_repo: Any, mock_consensus: Any, mock_hasher: Any
) -> None:
    mock_block_repo.get_latest_block.return_value = None
    mock_tx_repo.get_by_status.return_value = [pending_transaction()]
    mock_block_repo.create.side_effect = BlockHeightTakenError("Block 0 was just mined by another request; mine again")

    with pytest.raises(BlockHeightTakenError):
        await MineBlockUseCase(mock_block_repo, mock_tx_repo, mock_consensus, mock_hasher, **DEFAULTS).execute("miner1")

    mock_tx_repo.create.assert_not_called()
    mock_tx_repo.update.assert_not_called()


@pytest.mark.asyncio
async def test_the_difficulty_and_the_reward_are_the_ones_given(
    mock_block_repo: Any, mock_tx_repo: Any, mock_consensus: Any, mock_hasher: Any
) -> None:
    mock_block_repo.get_latest_block.return_value = None
    pending = pending_transaction()
    pending.fee = 0.25
    mock_tx_repo.get_by_status.return_value = [pending]

    use_case = MineBlockUseCase(mock_block_repo, mock_tx_repo, mock_consensus, mock_hasher, difficulty=3, reward=12.5)
    await use_case.execute("miner1")

    assert mock_consensus.mine_block.await_args.kwargs["difficulty"] == 3
    # The reward plus the block's fees
    assert mock_tx_repo.create.call_args.args[0].amount == 12.75
