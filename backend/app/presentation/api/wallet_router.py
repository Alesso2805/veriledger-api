from fastapi import APIRouter, Depends
from backend.app.application.dto.wallet import WalletKeyPairDTO
from backend.app.application.use_cases.wallet.generate_wallet import GenerateWalletUseCase
from backend.app.infrastructure.security.ed25519_service import Ed25519ServiceImpl

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("/generate", response_model=WalletKeyPairDTO)
async def generate_wallet() -> WalletKeyPairDTO:
    """
    Utility endpoint for testing. Generates a new Ed25519 key pair.
    The private key should ideally never leave the client's device, 
    but we provide this for testing purposes.
    """
    wallet_service = Ed25519ServiceImpl()
    use_case = GenerateWalletUseCase(wallet_service)
    
    return use_case.execute()
