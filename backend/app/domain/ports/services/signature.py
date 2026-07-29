from abc import ABC, abstractmethod


class SignatureService(ABC):
    @abstractmethod
    def verify_signature(self, public_key_hex: str, payload: str, signature_hex: str) -> bool:
        pass
