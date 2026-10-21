import hashlib
import json

from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import Transaction
from backend.app.domain.ports.services.hashing import HasherService


class SHA256HasherImpl(HasherService):
    def hash_transaction(self, transaction: Transaction) -> str:
        # What was signed plus the signature, and no id or arrival time: the same signed body is the same
        # transaction, and two signatures are two transactions (ADR-0004)
        tx_data: dict[str, str | int | None] = {
            "amount": f"{transaction.amount:.8f}",
            "fee": f"{transaction.fee:.8f}",
            "nonce": transaction.nonce,
            "receiver_address": transaction.receiver_address,
            "sender_address": transaction.sender_address,
            "signature": transaction.signature,
        }
        if transaction.payload is not None:
            tx_data["payload"] = transaction.payload
        tx_string = json.dumps(tx_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(tx_string.encode("utf-8")).hexdigest()

    def hash_block(self, block: Block) -> str:
        block_data = {
            "id": block.id,
            "block_number": block.block_number,
            "previous_hash": block.previous_hash,
            "timestamp": block.timestamp.isoformat(),
            "nonce": getattr(block, "nonce", 0),
            "transaction_ids": sorted(block.transaction_ids),
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()
