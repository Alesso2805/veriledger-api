import binascii
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from backend.app.domain.ports.services.signature import SignatureService
from backend.app.domain.ports.services.wallet import WalletService


class Ed25519ServiceImpl(SignatureService, WalletService):
    def generate_key_pair(self) -> tuple[str, str]:
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        return public_bytes.hex(), private_bytes.hex()

    def verify_signature(self, public_key_hex: str, payload: str, signature_hex: str) -> bool:
        try:
            public_bytes = bytes.fromhex(public_key_hex)
            signature_bytes = bytes.fromhex(signature_hex)
            payload_bytes = payload.encode("utf-8")

            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
            public_key.verify(signature_bytes, payload_bytes)
            return True
        except (ValueError, InvalidSignature, TypeError):
            # Hex decoding errors or verification failure
            return False
