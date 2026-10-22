from abc import ABC, abstractmethod
from typing import NamedTuple


class KeyPair(NamedTuple):
    public_key_hex: str
    private_key_hex: str


class WalletService(ABC):
    @abstractmethod
    def generate_key_pair(self) -> KeyPair:
        pass
