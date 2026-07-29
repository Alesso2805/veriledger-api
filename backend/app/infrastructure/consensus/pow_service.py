from backend.app.domain.entities.block import Block
from backend.app.domain.ports.services.consensus import ConsensusService
from backend.app.domain.ports.services.hashing import HasherService


class ProofOfWorkServiceImpl(ConsensusService):
    def __init__(self, hasher: HasherService):
        self.hasher = hasher

    def mine_block(self, block: Block, difficulty: int) -> tuple[int, str]:
        target = "0" * difficulty
        block.nonce = 0
        
        while True:
            # We use the hasher service to calculate the hash for the current nonce
            current_hash = self.hasher.hash_block(block)
            
            if current_hash.startswith(target):
                return block.nonce, current_hash
            
            block.nonce += 1
