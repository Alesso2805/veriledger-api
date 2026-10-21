import json
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from backend.app.domain.signed_message import build_signed_message
from backend.app.infrastructure.security.ed25519_service import Ed25519ServiceImpl

VECTORS: list[dict[str, Any]] = json.loads(
    (Path(__file__).resolve().parents[3] / "docs" / "signing-vectors.json").read_text(encoding="utf-8")
)["vectors"]


def test_the_vectors_cover_a_transfer_a_fee_and_a_notarization() -> None:
    names = {vector["name"] for vector in VECTORS}
    assert {"transfer", "transfer_with_fee", "notarization"} <= names
    assert any(vector["fields"].get("payload") for vector in VECTORS)


@pytest.mark.parametrize("vector", VECTORS, ids=[vector["name"] for vector in VECTORS])
def test_ar14_the_signed_message_reproduces_every_vector(vector: dict[str, Any]) -> None:
    message = build_signed_message(**vector["fields"])

    assert message.encode("utf-8") == vector["message"].encode("utf-8")
    assert Ed25519ServiceImpl().verify_signature(vector["public_key"], message, vector["signature"])


@pytest.mark.parametrize("vector", VECTORS, ids=[vector["name"] for vector in VECTORS])
def test_each_vector_is_consistent_with_its_key(vector: dict[str, Any]) -> None:
    key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(vector["private_key"]))
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    assert public == vector["public_key"] == vector["fields"]["sender_address"]
    # Ed25519 is deterministic: the same key and message give the same signature in any library
    assert key.sign(vector["message"].encode("utf-8")).hex() == vector["signature"]
