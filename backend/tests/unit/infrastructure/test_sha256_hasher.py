from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.infrastructure.security.sha256_hasher import SHA256HasherImpl

NOW = datetime.now(UTC)


def transaction(**changes: Any) -> Transaction:
    fields: dict[str, Any] = {
        "id": "id-1",
        "sender_address": "sender",
        "receiver_address": "receiver",
        "amount": 10.0,
        "fee": 0.1,
        "status": TransactionStatus.PENDING,
        "timestamp": NOW,
        "signature": "signature",
        "nonce": 1,
    }
    return Transaction(**{**fields, **changes})


def test_the_same_signed_body_has_the_same_hash_whatever_its_id_status_and_arrival() -> None:
    hasher = SHA256HasherImpl()
    replay = transaction(id="id-2", timestamp=NOW + timedelta(minutes=5), status=TransactionStatus.CONFIRMED)

    assert hasher.hash_transaction(transaction()) == hasher.hash_transaction(replay)


@pytest.mark.parametrize(
    "change",
    [
        {"signature": "another signature"},
        {"nonce": 2},
        {"fee": 0.2},
        {"amount": 11.0},
        {"payload": "document hash"},
        {"receiver_address": "someone else"},
        {"sender_address": "another sender"},
    ],
    ids=["signature", "nonce", "fee", "amount", "payload", "receiver", "sender"],
)
def test_every_signed_field_and_the_signature_change_the_hash(change: dict[str, Any]) -> None:
    hasher = SHA256HasherImpl()

    assert hasher.hash_transaction(transaction()) != hasher.hash_transaction(transaction(**change))
