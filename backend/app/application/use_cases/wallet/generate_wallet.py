from backend.app.application.dto.wallet import WalletKeyPairDTO
from backend.app.domain.ports.services.wallet import WalletService


class GenerateWalletUseCase:
    def __init__(self, wallet_service: WalletService):
        self.wallet_service = wallet_service

    def execute(self) -> WalletKeyPairDTO:
        public_key, private_key = self.wallet_service.generate_key_pair()
        return WalletKeyPairDTO(public_key=public_key, private_key=private_key)
