from abc import ABC, abstractmethod


class WalletService(ABC):
    @abstractmethod
    def generate_key_pair(self) -> tuple[str, str]:
        """
        Generates a new key pair.
        Returns:
            tuple[str, str]: A tuple containing (public_key_hex, private_key_hex)
        """
        pass
