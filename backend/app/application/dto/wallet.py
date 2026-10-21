from pydantic import BaseModel


class WalletKeyPairDTO(BaseModel):
    public_key: str
    private_key: str


class NonceResponseDTO(BaseModel):
    address: str
    nonce: int


class BalanceResponseDTO(BaseModel):
    address: str
    balance: float
