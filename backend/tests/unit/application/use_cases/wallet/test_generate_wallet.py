import pytest
from unittest.mock import create_autospec

from backend.app.application.use_cases.wallet.generate_wallet import GenerateWalletUseCase
from backend.app.domain.ports.services.wallet import WalletService

def test_generate_wallet_success():
    mock_wallet_service = create_autospec(WalletService, instance=True)
    mock_wallet_service.generate_key_pair.return_value = ("pub_key", "priv_key")
    
    use_case = GenerateWalletUseCase(mock_wallet_service)
    result = use_case.execute()
    
    assert result.public_key == "pub_key"
    assert result.private_key == "priv_key"
    mock_wallet_service.generate_key_pair.assert_called_once()
