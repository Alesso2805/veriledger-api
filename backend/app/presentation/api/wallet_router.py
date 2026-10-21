from fastapi import APIRouter

from backend.app.application.dto.wallet import BalanceResponseDTO, NonceResponseDTO, WalletKeyPairDTO
from backend.app.application.use_cases.wallet.generate_wallet import GenerateWalletUseCase
from backend.app.application.use_cases.wallet.get_balance import GetBalanceUseCase
from backend.app.application.use_cases.wallet.get_next_nonce import GetNextNonceUseCase
from backend.app.infrastructure.repositories.transaction_repository_impl import TransactionRepositoryImpl
from backend.app.infrastructure.security.ed25519_service import Ed25519ServiceImpl
from backend.app.presentation.dependencies.database import DbSession

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("/generate", response_model=WalletKeyPairDTO)
async def generate_wallet() -> WalletKeyPairDTO:
    """
    Development helper. The private key travels over the network, so production answers 404 (VLA-21)
    and the webapp generates keys in the browser (VLW-16).
    """
    wallet_service = Ed25519ServiceImpl()
    use_case = GenerateWalletUseCase(wallet_service)

    return use_case.execute()


@router.get("/{address}/balance", response_model=BalanceResponseDTO)
async def get_balance(
    address: str,
    db: DbSession,
) -> BalanceResponseDTO:
    tx_repo = TransactionRepositoryImpl(db)
    use_case = GetBalanceUseCase(tx_repo)
    balance = await use_case.execute(address)
    return BalanceResponseDTO(address=address, balance=balance)


@router.get("/{address}/nonce", response_model=NonceResponseDTO)
async def get_next_nonce(
    address: str,
    db: DbSession,
) -> NonceResponseDTO:
    nonce = await GetNextNonceUseCase(TransactionRepositoryImpl(db)).execute(address)
    return NonceResponseDTO(address=address, nonce=nonce)
