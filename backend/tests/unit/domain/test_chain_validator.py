from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from backend.app.domain.chain_validator import GENESIS_PREVIOUS_HASH, ChainValidator
from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.signed_message import build_signed_message
from backend.app.infrastructure.security.ed25519_service import Ed25519ServiceImpl
from backend.app.infrastructure.security.sha256_hasher import SHA256HasherImpl

DIFFICULTY = 2
REWARD = 50.0
START = datetime(2026, 10, 21, 12, 0, 0, 123456, tzinfo=UTC)
hasher = SHA256HasherImpl()
validator = ChainValidator(hasher, Ed25519ServiceImpl(), difficulty=DIFFICULTY, reward=REWARD)


class Wallet:
    def __init__(self) -> None:
        self.key = ed25519.Ed25519PrivateKey.generate()
        self.address = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


ALICE, BOB, MINER = Wallet(), Wallet(), Wallet()


def written(moment: datetime) -> str:
    # How Pydantic writes a UTC datetime in /blocks/full
    return moment.isoformat().replace("+00:00", "Z")


def hashed(transaction: dict[str, Any]) -> dict[str, Any]:
    entity = Transaction(
        id=transaction["id"],
        sender_address=transaction["sender_address"],
        receiver_address=transaction["receiver_address"],
        amount=transaction["amount"],
        fee=transaction["fee"],
        status=TransactionStatus.CONFIRMED,
        timestamp=START,
        signature=transaction["signature"],
        payload=transaction["payload"],
        nonce=transaction["nonce"],
    )
    return {**transaction, "tx_hash": hasher.hash_transaction(entity)}


def signed(
    sender: Wallet, receiver: str, amount: str, fee: str, nonce: int, payload: str | None = None
) -> dict[str, Any]:
    message = build_signed_message(
        sender_address=sender.address, receiver_address=receiver, amount=amount, fee=fee, nonce=nonce, payload=payload
    )
    return hashed(
        {
            "id": f"tx-{sender.address[:8]}-{nonce}-{receiver[:4]}",
            "sender_address": sender.address,
            "receiver_address": receiver,
            "amount": float(amount),
            "fee": float(fee),
            "status": "CONFIRMED",
            "timestamp": written(START),
            "signature": sender.key.sign(message.encode("utf-8")).hex(),
            "nonce": nonce,
            "payload": payload,
        }
    )


def coinbase(
    number: int, fees: float = 0.0, *, to: str = MINER.address, amount: float | None = None, nonce: int | None = None
) -> dict[str, Any]:
    return hashed(
        {
            "id": f"coinbase-{number}-{to[:4]}",
            "sender_address": "SYSTEM",
            "receiver_address": to,
            "amount": REWARD + fees if amount is None else amount,
            "fee": 0.0,
            "status": "CONFIRMED",
            "timestamp": written(START),
            "signature": "COINBASE",
            "nonce": number if nonce is None else nonce,
            "payload": None,
        }
    )


def seal(block: dict[str, Any], difficulty: int = DIFFICULTY) -> dict[str, Any]:
    """Finds the block's nonce and hash, as a miner would."""
    entity = Block(
        id=block["id"],
        block_number=block["block_number"],
        previous_hash=block["previous_hash"],
        timestamp=datetime.fromisoformat(block["timestamp"]),
        transaction_ids=[transaction["id"] for transaction in block["transactions"]],
    )
    while not (block_hash := hasher.hash_block(entity)).startswith("0" * difficulty):
        entity.nonce += 1
    return {**block, "nonce": entity.nonce, "block_hash": block_hash}


def chain_of(*blocks_transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Seals each block on the one before and serves them as /blocks/full does: newest first."""
    blocks: list[dict[str, Any]] = []
    for number, transactions in enumerate(blocks_transactions):
        block = {
            "id": f"block-{number}",
            "block_number": number,
            "previous_hash": blocks[-1]["block_hash"] if blocks else GENESIS_PREVIOUS_HASH,
            "timestamp": written(START + timedelta(minutes=number)),
            "transactions": transactions,
        }
        blocks.append(seal(block))
    return list(reversed(blocks))


def history() -> list[list[dict[str, Any]]]:
    """Alice is paid a reward, pays Bob and notarizes a document in one block, then Bob pays the miner."""
    return [
        [coinbase(0, to=ALICE.address)],
        [
            signed(ALICE, BOB.address, "10.00000000", "0.50000000", 1),
            # A zero fee, which must still be signed as "0.00000000"
            signed(ALICE, ALICE.address, "0.00000000", "0.00000000", 2, payload="9f86d081884c7d65"),
            coinbase(1, fees=0.5),
        ],
        [signed(BOB, MINER.address, "4.00000000", "0.00000000", 1), coinbase(2)],
    ]


def newest_first_blocks() -> list[dict[str, Any]]:
    return chain_of(*history())


def reason(blocks_transactions: list[list[dict[str, Any]]]) -> str | None:
    return validator.violation(chain_of(*blocks_transactions))


def test_a_mined_history_keeps_every_rule() -> None:
    assert reason(history()) is None


def test_the_order_of_a_blocks_transactions_does_not_matter() -> None:
    blocks = history()
    blocks[1].reverse()

    assert reason(blocks) is None


def test_an_empty_chain_is_refused() -> None:
    assert validator.violation([]) == "the chain is empty"


def test_a_chain_that_does_not_start_at_genesis_is_refused() -> None:
    chain = newest_first_blocks()
    chain[-1] = seal({**chain[-1], "previous_hash": "1" * 64})

    assert validator.violation(chain) == "the chain does not start at a genesis block"


def test_a_chain_with_a_missing_block_is_refused() -> None:
    chain = newest_first_blocks()
    del chain[1]

    assert validator.violation(chain) == "block numbers are not consecutive: block 2 where 1 belongs"


def test_a_block_that_points_elsewhere_is_refused_even_with_a_valid_hash() -> None:
    chain = newest_first_blocks()
    # Re-sealed, so its own hash and difficulty hold and only the link breaks
    chain[1] = seal({**chain[1], "previous_hash": "0" * 4 + "f" * 60})

    assert validator.violation(chain) == "block 1 does not point at block 0"


def test_a_block_whose_transaction_list_changed_is_refused() -> None:
    chain = newest_first_blocks()
    chain[0] = {**chain[0], "transactions": [*chain[0]["transactions"], coinbase(2, to=BOB.address)]}

    assert validator.violation(chain) == "block 2's hash does not match its contents"


def test_a_block_below_the_difficulty_is_refused() -> None:
    chain = newest_first_blocks()
    # A real hash of the block, found with less work than this node asks for
    for minute in range(10):
        easy = seal({**chain[0], "timestamp": written(START + timedelta(hours=1, minutes=minute))}, difficulty=0)
        if not easy["block_hash"].startswith("0" * DIFFICULTY):
            break
    chain[0] = easy

    assert validator.violation(chain) == "block 2 does not meet the difficulty"


@pytest.mark.parametrize("field", ["id", "timestamp", "transactions", "block_hash"])
def test_a_malformed_block_is_refused(field: str) -> None:
    chain = newest_first_blocks()
    del chain[1][field]

    assert validator.violation(chain) == "a block is malformed"


def test_a_block_without_a_coinbase_is_refused() -> None:
    blocks = history()
    blocks[2] = blocks[2][:1]

    assert reason(blocks) == "block 2 has no coinbase"


def test_a_block_with_two_coinbases_is_refused() -> None:
    blocks = history()
    blocks[2].append(coinbase(2, to=BOB.address))

    assert reason(blocks) == "block 2 has more than one coinbase"


def test_a_coinbase_that_pays_more_than_the_reward_and_the_fees_is_refused() -> None:
    blocks = history()
    blocks[1][2] = coinbase(1, amount=60.0)

    assert reason(blocks) == "block 1's coinbase pays 60.00000000, not the reward plus fees, 50.50000000"


def test_a_coinbase_without_the_block_number_as_its_nonce_is_refused() -> None:
    blocks = history()
    blocks[1][2] = coinbase(1, fees=0.5, nonce=7)

    assert reason(blocks) == "block 1's coinbase does not carry the block number as its nonce"


def test_a_transaction_changed_after_it_was_hashed_is_refused() -> None:
    blocks = history()
    blocks[1][0] = {**blocks[1][0], "amount": 11.0}

    assert reason(blocks) == f"transaction {blocks[1][0]['tx_hash'][:12]}'s hash does not match its contents"


def test_a_transaction_whose_signature_covers_something_else_is_refused() -> None:
    blocks = history()
    # Hashed again, so only the signature gives it away
    blocks[1][0] = hashed({**blocks[1][0], "amount": 11.0})

    assert reason(blocks) == f"transaction {blocks[1][0]['tx_hash'][:12]}'s signature does not verify"


def test_a_skipped_nonce_is_refused() -> None:
    blocks = history()
    blocks[1][1] = signed(ALICE, ALICE.address, "0.00000000", "0.00000000", 3, payload="9f86d081884c7d65")

    assert reason(blocks) == f"transaction {blocks[1][1]['tx_hash'][:12]} has nonce 3 where its sender's next is 2"


def test_a_reused_nonce_is_refused() -> None:
    blocks = history()
    blocks[2].append(signed(ALICE, MINER.address, "1.00000000", "0.00000000", 1))

    assert reason(blocks) == f"transaction {blocks[2][-1]['tx_hash'][:12]} has nonce 1 where its sender's next is 3"


def test_spending_more_than_the_sender_has_is_refused() -> None:
    blocks = history()
    blocks[1][0] = signed(ALICE, BOB.address, "60.00000000", "0.50000000", 1)

    assert (
        reason(blocks) == f"transaction {blocks[1][0]['tx_hash'][:12]} spends more than its sender had before block 1"
    )


def test_money_received_in_a_block_cannot_be_spent_in_the_same_block() -> None:
    blocks = history()
    # Bob's 10 arrive in block 1, so in block 1 he still has nothing
    bobs = signed(BOB, MINER.address, "4.00000000", "0.00000000", 1)
    blocks[1].insert(2, bobs)
    blocks[2] = [coinbase(2)]

    assert reason(blocks) == f"transaction {bobs['tx_hash'][:12]} spends more than its sender had before block 1"


@pytest.mark.parametrize("field", ["signature", "nonce", "tx_hash", "sender_address"])
def test_a_malformed_transaction_is_refused(field: str) -> None:
    blocks = history()
    del blocks[1][0][field]

    assert reason(blocks) == "a block is malformed"
