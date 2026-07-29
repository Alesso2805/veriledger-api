import httpx
from typing import List

from backend.app.domain.entities.block import Block
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.repositories.block_repository import BlockRepository

class ResolveConflictsUseCase:
    def __init__(self, node_repo: NodeRepository, block_repo: BlockRepository):
        self._node_repo = node_repo
        self._block_repo = block_repo

    async def execute(self) -> bool:
        """
        Polls all registered peers, finds the longest valid chain, and replaces ours if needed.
        Returns True if our chain was replaced.
        """
        nodes = await self._node_repo.get_all()
        our_blocks = await self._block_repo.get_all_blocks()
        max_length = len(our_blocks)
        new_chain: List[Block] | None = None

        async with httpx.AsyncClient() as client:
            for node in nodes:
                try:
                    response = await client.get(f"{node.url}/blocks/full")
                    if response.status_code == 200:
                        data = response.json()
                        length = data.get("total", 0)
                        items = data.get("items", [])
                        
                        if length > max_length and self._is_valid_chain(items):
                            max_length = length
                            new_chain = items
                except httpx.RequestError:
                    continue
        
        if new_chain:
            # We found a longer valid chain. Replace ours.
            await self._block_repo.replace_chain(new_chain)
            return True
        
        return False

    def _is_valid_chain(self, chain_data: list[dict]) -> bool:
        """
        Validate the new chain hashes and proof of work.
        For MVP, we just do a simple structural check.
        """
        if not chain_data:
            return False
            
        last_block = chain_data[0]
        for current_block in chain_data[1:]:
            # Verify previous hash (Note: assuming chain is ordered oldest to newest, wait, our get_all returns newest first)
            # Actually get_all_blocks returns offset ordered by DESC. So items[0] is the NEWEST block.
            # So items[i] should have previous_hash == items[i+1].block_hash
            if current_block.get("block_hash") != last_block.get("previous_hash"):
                return False
            last_block = current_block
            
        return True
