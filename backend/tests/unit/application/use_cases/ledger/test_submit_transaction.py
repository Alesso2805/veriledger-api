import pytest
import uuid
from unittest.mock import create_autospec, AsyncMock, patch
from datetime import datetime, timezone

from backend.app.application.dto.transaction import TransactionCreateRequestDTO
from backend.app.application.use_cases.ledger.submit_transaction import SubmitTransactionUseCase
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.services.hashing import HasherService
from backend.app.domain.ports.services.signature import SignatureService

@pytest.fixture
def mock_tx_repo():
    return create_autospec(TransactionRepository, instance=True)

@pytest.fixture
def mock_node_repo():
    return create_autospec(NodeRepository, instance=True)

@pytest.fixture
def mock_hasher():
    hasher = create_autospec(HasherService, instance=True)
    hasher.hash_transaction.return_value = "mocked_tx_hash"
    return hasher

@pytest.fixture
def mock_signature_service():
    sig = create_autospec(SignatureService, instance=True)
    sig.verify_signature.return_value = True
    return sig

@pytest.mark.asyncio
async def test_submit_transaction_success(mock_tx_repo, mock_hasher, mock_signature_service, mock_node_repo):
    use_case = SubmitTransactionUseCase(mock_tx_repo, mock_hasher, mock_signature_service, mock_node_repo)
    request = TransactionCreateRequestDTO(
        sender_address="sender",
        receiver_address="receiver",
        amount=10.0,
        fee=1.0,
        signature="valid_sig"
    )
    
    mock_tx_repo.get_by_hash.return_value = None 
    mock_tx_repo.get_balance.return_value = 100.0 
    
    async def mock_create(tx):
        return tx
    mock_tx_repo.create.side_effect = mock_create
    
    with patch("asyncio.create_task") as mock_create_task:
        result = await use_case.execute(request)
        
        assert result.sender_address == "sender"
        assert result.amount == 10.0
        assert result.tx_hash == "mocked_tx_hash"
        assert result.status == TransactionStatus.PENDING
        
        mock_tx_repo.create.assert_called_once()
        mock_create_task.assert_called_once()

@pytest.mark.asyncio
async def test_submit_transaction_insufficient_funds(mock_tx_repo, mock_hasher, mock_signature_service):
    use_case = SubmitTransactionUseCase(mock_tx_repo, mock_hasher, mock_signature_service)
    request = TransactionCreateRequestDTO(
        sender_address="sender",
        receiver_address="receiver",
        amount=100.0,
        fee=1.0,
        signature="valid_sig"
    )
    
    mock_tx_repo.get_by_hash.return_value = None
    mock_tx_repo.get_balance.return_value = 50.0 
    
    with pytest.raises(ValueError, match="Insufficient funds"):
        await use_case.execute(request)

@pytest.mark.asyncio
async def test_submit_transaction_already_exists(mock_tx_repo, mock_hasher, mock_signature_service):
    use_case = SubmitTransactionUseCase(mock_tx_repo, mock_hasher, mock_signature_service)
    request = TransactionCreateRequestDTO(
        sender_address="sender",
        receiver_address="receiver",
        amount=10.0,
        fee=1.0,
        signature="valid_sig"
    )
    
    existing_tx = Transaction(
        id="123", sender_address="s", receiver_address="r", amount=1.0, fee=1.0, status=TransactionStatus.PENDING, timestamp=datetime.now(timezone.utc), signature="sig"
    )
    mock_tx_repo.get_by_hash.return_value = existing_tx
    
    result = await use_case.execute(request)
    assert result == existing_tx
    mock_tx_repo.get_balance.assert_not_called()
