from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import Transaction, TransactionStatus
from backend.app.domain.ports.services.hashing import HasherService
from backend.app.domain.ports.services.signature import SignatureService
from backend.app.domain.signed_message import build_signed_message, next_nonce

GENESIS_PREVIOUS_HASH = "0" * 64
COINBASE_SENDER = "SYSTEM"


def spelled(value: Any) -> str:
    # The signed spelling (ADR-0004); str(Decimal) would write a zero fee as "0E-8"
    return f"{float(value):.8f}"


def amount(value: Any) -> Decimal:
    # Sums in Decimal do not drift, but the value passes through float: exact only to about 15 digits (VLA-31)
    return Decimal(spelled(value))


class ChainValidator:
    """SPEC › Valid chain: whether a peer's chain, as /blocks/full serves it, may replace ours (VLA-18)."""

    def __init__(self, hasher: HasherService, signature_service: SignatureService, difficulty: int, reward: float):
        self._hasher = hasher
        self._signature_service = signature_service
        self._target = "0" * difficulty
        self._reward = amount(reward)

    def violation(self, chain: list[dict[str, Any]]) -> str | None:
        """The first rule the chain breaks, in words, or None when it keeps them all."""
        if not chain:
            return "the chain is empty"
        # /blocks/full lists the newest block first; the rules read from the genesis up
        blocks = list(reversed(chain))
        balances: dict[str, Decimal] = defaultdict(Decimal)
        last_nonces: dict[str, int] = {}
        try:
            for number, block in enumerate(blocks):
                reason = self._block_violation(block, blocks[number - 1] if number else None, number)
                reason = reason or self._transactions_violation(block, number, balances, last_nonces)
                if reason:
                    return reason
        except (KeyError, TypeError, ValueError, AttributeError):
            return "a block is malformed"
        return None

    def _block_violation(self, block: dict[str, Any], previous: dict[str, Any] | None, number: int) -> str | None:
        if block["block_number"] != number:
            return f"block numbers are not consecutive: block {block['block_number']} where {number} belongs"
        if previous is None and block["previous_hash"] != GENESIS_PREVIOUS_HASH:
            return "the chain does not start at a genesis block"
        if previous is not None and block["previous_hash"] != previous["block_hash"]:
            return f"block {number} does not point at block {number - 1}"
        recomputed = self._hasher.hash_block(
            Block(
                id=block["id"],
                block_number=number,
                previous_hash=block["previous_hash"],
                # Pydantic writes UTC as "Z"; read back, it hashes as the miner's "+00:00" did
                timestamp=datetime.fromisoformat(block["timestamp"]),
                nonce=block["nonce"],
                transaction_ids=[transaction["id"] for transaction in block["transactions"]],
            )
        )
        if block["block_hash"] != recomputed:
            return f"block {number}'s hash does not match its contents"
        if not recomputed.startswith(self._target):
            return f"block {number} does not meet the difficulty"
        return None

    def _transactions_violation(
        self, block: dict[str, Any], number: int, balances: dict[str, Decimal], last_nonces: dict[str, int]
    ) -> str | None:
        transactions = block["transactions"]
        for transaction in transactions:
            if self._hasher.hash_transaction(self._entity(transaction)) != transaction["tx_hash"]:
                return f"transaction {transaction['tx_hash'][:12]}'s hash does not match its contents"
        coinbases = [tx for tx in transactions if tx["sender_address"] == COINBASE_SENDER]
        transfers = [tx for tx in transactions if tx["sender_address"] != COINBASE_SENDER]
        return self._coinbase_violation(coinbases, transfers, number) or self._transfers_violation(
            transactions, transfers, number, balances, last_nonces
        )

    def _coinbase_violation(
        self, coinbases: list[dict[str, Any]], transfers: list[dict[str, Any]], number: int
    ) -> str | None:
        if not coinbases:
            return f"block {number} has no coinbase"
        if len(coinbases) > 1:
            return f"block {number} has more than one coinbase"
        coinbase = coinbases[0]
        due = self._reward + sum((amount(tx["fee"]) for tx in transfers), Decimal())
        if amount(coinbase["amount"]) != due:
            return f"block {number}'s coinbase pays {spelled(coinbase['amount'])}, not the reward plus fees, {due:.8f}"
        if coinbase["nonce"] != number:
            return f"block {number}'s coinbase does not carry the block number as its nonce"
        return None

    def _transfers_violation(
        self,
        transactions: list[dict[str, Any]],
        transfers: list[dict[str, Any]],
        number: int,
        balances: dict[str, Decimal],
        last_nonces: dict[str, int],
    ) -> str | None:
        # A block's transactions were all pending together, so each was checked against the balance before the
        # block, less what its sender was already spending; the order /blocks/full lists them in is not theirs
        spending: dict[str, Decimal] = defaultdict(Decimal)
        for transaction in sorted(transfers, key=lambda tx: (tx["sender_address"], tx["nonce"])):
            name = f"transaction {transaction['tx_hash'][:12]}"
            if not self._signature_verifies(transaction):
                return f"{name}'s signature does not verify"
            sender = transaction["sender_address"]
            expected = next_nonce(last_nonces.get(sender))
            if transaction["nonce"] != expected:
                return f"{name} has nonce {transaction['nonce']} where its sender's next is {expected}"
            last_nonces[sender] = expected
            spending[sender] += amount(transaction["amount"]) + amount(transaction["fee"])
            if spending[sender] > balances[sender]:
                return f"{name} spends more than its sender had before block {number}"

        for transaction in transactions:
            balances[transaction["receiver_address"]] += amount(transaction["amount"])
        for sender, spent in spending.items():
            balances[sender] -= spent
        return None

    def _signature_verifies(self, transaction: dict[str, Any]) -> bool:
        message = build_signed_message(
            sender_address=transaction["sender_address"],
            receiver_address=transaction["receiver_address"],
            amount=spelled(transaction["amount"]),
            fee=spelled(transaction["fee"]),
            nonce=transaction["nonce"],
            payload=transaction.get("payload"),
        )
        return self._signature_service.verify_signature(
            transaction["sender_address"], message, transaction["signature"]
        )

    @staticmethod
    def _entity(transaction: dict[str, Any]) -> Transaction:
        return Transaction(
            id=transaction["id"],
            sender_address=transaction["sender_address"],
            receiver_address=transaction["receiver_address"],
            amount=float(transaction["amount"]),
            fee=float(transaction["fee"]),
            status=TransactionStatus.CONFIRMED,
            timestamp=datetime.fromisoformat(transaction["timestamp"]),
            signature=transaction["signature"],
            payload=transaction.get("payload"),
            nonce=transaction["nonce"],
        )
