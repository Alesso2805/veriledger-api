from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.dto.wallet import WalletKeyPairDTO
from backend.app.application.use_cases.wallet.generate_wallet import GenerateWalletUseCase
from backend.app.application.use_cases.wallet.get_balance import GetBalanceUseCase
from backend.app.infrastructure.database import get_db_session
from backend.app.infrastructure.repositories.transaction_repository_impl import TransactionRepositoryImpl
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


@router.get("/{address}/balance")
async def get_balance(
    address: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    tx_repo = TransactionRepositoryImpl(db)
    use_case = GetBalanceUseCase(tx_repo)
    balance = await use_case.execute(address)
    return {"address": address, "balance": balance}
