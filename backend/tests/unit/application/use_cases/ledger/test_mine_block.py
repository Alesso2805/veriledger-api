import pytest
import uuid
from unittest.mock import create_autospec, AsyncMock, patch
from datetime import datetime, timezone

from backend.app.application.use_cases.ledger.mine_block import MineBlockUseCase
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.entities.block import Block
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.services.consensus import ConsensusService
from backend.app.domain.ports.services.hashing import HasherService

@pytest.fixture
def mock_block_repo():
    return create_autospec(BlockRepository, instance=True)

@pytest.fixture
def mock_tx_repo():
    return create_autospec(TransactionRepository, instance=True)

@pytest.fixture
def mock_consensus():
    c = create_autospec(ConsensusService, instance=True)
    c.mine_block.return_value = (123, "new_block_hash")
    return c

@pytest.fixture
def mock_hasher():
    h = create_autospec(HasherService, instance=True)
    h.hash_transaction.return_value = "coinbase_tx_hash"
    return h

@pytest.fixture
def mock_node_repo():
    return create_autospec(NodeRepository, instance=True)

@pytest.mark.asyncio
async def test_mine_block_success(mock_block_repo, mock_tx_repo, mock_consensus, mock_hasher, mock_node_repo):
    use_case = MineBlockUseCase(mock_block_repo, mock_tx_repo, mock_consensus, mock_hasher, mock_node_repo)
    
    pending_tx = Transaction(
        id="tx1", sender_address="s", receiver_address="r", amount=10.0, fee=2.0, status=TransactionStatus.PENDING, timestamp=datetime.now(timezone.utc), signature="sig"
    )
    mock_tx_repo.get_by_status.return_value = [pending_tx]
    
    last_block = Block(
        id="b1", block_number=5, previous_hash="prev", timestamp=datetime.now(timezone.utc), transaction_ids=[]
    )
    last_block.block_hash = "last_hash"
    mock_block_repo.get_latest_block.return_value = last_block
    
    with patch("asyncio.create_task") as mock_create_task:
        result = await use_case.execute("miner1")
        
        assert result.block_number == 6
        assert result.previous_hash == "last_hash"
        assert result.nonce == 123
        assert result.block_hash == "new_block_hash"
        assert len(result.transaction_ids) == 2 # 1 coinbase + 1 pending
        
        mock_tx_repo.create.assert_called_once()
        mock_block_repo.create.assert_called_once()
        mock_create_task.assert_called_once() # Broadcasting triggered
