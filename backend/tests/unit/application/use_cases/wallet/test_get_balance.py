import pytest
from unittest.mock import create_autospec

from backend.app.application.use_cases.wallet.get_balance import GetBalanceUseCase
from backend.app.domain.ports.repositories.transaction_repository import TransactionRepository

@pytest.fixture
def mock_tx_repo():
    return create_autospec(TransactionRepository, instance=True)

@pytest.mark.asyncio
async def test_get_balance_success(mock_tx_repo):
    use_case = GetBalanceUseCase(mock_tx_repo)
    
    mock_tx_repo.get_balance.return_value = 100.50
    
    result = await use_case.execute("address123")
    
    assert result == 100.50
    mock_tx_repo.get_balance.assert_called_once_with("address123")
