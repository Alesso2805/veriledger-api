from typing import Any

from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.services.peer_client import PeerClient


class ResolveConflictsUseCase:
    def __init__(self, node_repo: NodeRepository, block_repo: BlockRepository, peer_client: PeerClient):
        self._node_repo = node_repo
        self._block_repo = block_repo
        self._peer_client = peer_client

    async def execute(self) -> bool:
        """
        Polls all registered peers, finds the longest valid chain, and replaces ours if needed.
        Returns True if our chain was replaced.
        """
        nodes = await self._node_repo.get_all()
        # The whole local chain, not one page of it
        max_length = await self._block_repo.count()
        new_chain: list[dict[str, Any]] | None = None

        for node in nodes:
            chain = await self._peer_client.fetch_chain(node.url)
            # The length is what was fetched, never the total a peer claims
            if chain is not None and len(chain) > max_length and self._is_valid_chain(chain):
                max_length = len(chain)
                new_chain = chain

        if new_chain:
            await self._block_repo.replace_chain(new_chain)
            return True

        return False

    def _is_valid_chain(self, chain_data: list[dict[str, Any]]) -> bool:
        """Only checks that the blocks link up. SPEC › Valid chain lists the full rules, which VLA-18 implements."""
        if not chain_data:
            return False

        last_block = chain_data[0]
        for current_block in chain_data[1:]:
            # /blocks/full lists newest first, so each block's previous_hash must be the next item's block_hash
            if current_block.get("block_hash") != last_block.get("previous_hash"):
                return False
            last_block = current_block

        return True
