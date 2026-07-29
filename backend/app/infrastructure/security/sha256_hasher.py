import hashlib
import json

from backend.app.domain.entities.block import Block
from backend.app.domain.entities.transaction import Transaction
from backend.app.domain.ports.services.hashing import HasherService


class SHA256HasherImpl(HasherService):
    def hash_transaction(self, transaction: Transaction) -> str:
        # Create a deterministic dictionary representing the transaction
        tx_data = {
            "id": transaction.id,
            "sender_address": transaction.sender_address,
            "receiver_address": transaction.receiver_address,
            "amount": float(transaction.amount),
            "timestamp": transaction.timestamp.isoformat(),
        }
        # Dump to JSON with sorted keys to ensure determinism
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_string.encode("utf-8")).hexdigest()

    def hash_block(self, block: Block) -> str:
        block_data = {
            "id": block.id,
            "block_number": block.block_number,
            "previous_hash": block.previous_hash,
            "timestamp": block.timestamp.isoformat(),
            "nonce": getattr(block, 'nonce', 0),
            "transaction_ids": sorted(block.transaction_ids),
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()
