from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, create_autospec, patch

import pytest

from backend.app.application.dto.transaction import TransactionCreateRequestDTO
from backend.app.application.use_cases.ledger.submit_transaction import SubmitTransactionUseCase
from backend.app.domain.entities.node import Node
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.errors import NonceConflictError
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository
from backend.app.domain.ports.services.hashing import HasherService
from backend.app.domain.ports.services.signature import SignatureService


@pytest.fixture
def mock_tx_repo() -> Any:
    return create_autospec(TransactionRepository, instance=True)


@pytest.fixture
def mock_node_repo() -> Any:
    return create_autospec(NodeRepository, instance=True)


@pytest.fixture
def mock_hasher() -> Any:
    hasher = create_autospec(HasherService, instance=True)
    hasher.hash_transaction.return_value = "mocked_tx_hash"
    return hasher


@pytest.fixture
def mock_signature_service() -> Any:
    sig = create_autospec(SignatureService, instance=True)
    sig.verify_signature.return_value = True
    return sig


@pytest.mark.asyncio
async def test_submit_transaction_success(
    mock_tx_repo: Any, mock_hasher: Any, mock_signature_service: Any, mock_node_repo: Any
) -> None:
    use_case = SubmitTransactionUseCase(mock_tx_repo, mock_hasher, mock_signature_service, mock_node_repo)
    request = TransactionCreateRequestDTO(
        sender_address="sender",
        receiver_address="receiver",
        amount="10.00000000",
        fee="1.00000000",
        nonce=1,
        signature="valid_sig",
    )

    mock_tx_repo.get_by_hash.return_value = None
    mock_tx_repo.get_last_nonce.return_value = None
    mock_tx_repo.get_balance.return_value = 100.0

    async def mock_create(tx: Any) -> Any:
        return tx

    mock_tx_repo.create.side_effect = mock_create

    mock_node_repo.get_all.return_value = [Node(id="1", url="http://peer", status="ACTIVE")]

    result, created = await use_case.execute(request)

    assert created is True
    assert result.sender_address == "sender"
    assert result.amount == 10.0
    assert result.tx_hash == "mocked_tx_hash"
    assert result.status == TransactionStatus.PENDING
    assert result.nonce == 1
    mock_tx_repo.create.assert_called_once()

    # The router sends it after the response; execute only reads the peers while the session is open
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        await use_case.broadcast_transaction(request)
    mock_post.assert_awaited_once_with("http://peer/transactions", json=request.model_dump())


@pytest.mark.asyncio
async def test_submit_transaction_insufficient_funds(
    mock_tx_repo: Any, mock_hasher: Any, mock_signature_service: Any
) -> None:
    use_case = SubmitTransactionUseCase(mock_tx_repo, mock_hasher, mock_signature_service)
    request = TransactionCreateRequestDTO(
        sender_address="sender",
        receiver_address="receiver",
        amount="100.00000000",
        fee="1.00000000",
        nonce=1,
        signature="valid_sig",
    )

    mock_tx_repo.get_by_hash.return_value = None
    mock_tx_repo.get_last_nonce.return_value = None
    mock_tx_repo.get_balance.return_value = 50.0

    with pytest.raises(ValueError, match="Insufficient funds"):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_submit_transaction_already_exists(
    mock_tx_repo: Any, mock_hasher: Any, mock_signature_service: Any
) -> None:
    use_case = SubmitTransactionUseCase(mock_tx_repo, mock_hasher, mock_signature_service)
    request = TransactionCreateRequestDTO(
        sender_address="sender",
        receiver_address="receiver",
        amount="10.00000000",
        fee="1.00000000",
        nonce=1,
        signature="valid_sig",
    )

    existing_tx = Transaction(
        id="123",
        sender_address="s",
        receiver_address="r",
        amount=1.0,
        fee=1.0,
        status=TransactionStatus.PENDING,
        timestamp=datetime.now(UTC),
        signature="sig",
    )
    mock_tx_repo.get_by_hash.return_value = existing_tx

    result, created = await use_case.execute(request)
    assert (result, created) == (existing_tx, False)
    mock_tx_repo.get_balance.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(("last_nonce", "sent", "expected"), [(3, 3, 4), (3, 5, 4), (None, 2, 1)])
async def test_a_nonce_that_is_not_the_next_one_is_a_conflict(
    mock_tx_repo: Any, mock_hasher: Any, mock_signature_service: Any, last_nonce: int | None, sent: int, expected: int
) -> None:
    # Reused, skipped, and a first transaction that does not start at 1
    use_case = SubmitTransactionUseCase(mock_tx_repo, mock_hasher, mock_signature_service)
    request = TransactionCreateRequestDTO(
        sender_address="sender", receiver_address="receiver", amount="1.00000000", nonce=sent, signature="valid_sig"
    )
    mock_tx_repo.get_by_hash.return_value = None
    mock_tx_repo.get_last_nonce.return_value = last_nonce

    with pytest.raises(NonceConflictError, match=f"the next is {expected}"):
        await use_case.execute(request)
    mock_tx_repo.create.assert_not_called()
