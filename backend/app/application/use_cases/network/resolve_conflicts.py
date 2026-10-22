import logging
from typing import Any

from backend.app.domain.chain_validator import ChainValidator
from backend.app.domain.ports.repositories.block_repository import BlockRepository
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.services.peer_client import PeerClient

logger = logging.getLogger(__name__)


class ResolveConflictsUseCase:
    def __init__(
        self,
        node_repo: NodeRepository,
        block_repo: BlockRepository,
        peer_client: PeerClient,
        validator: ChainValidator,
    ):
        self._node_repo = node_repo
        self._block_repo = block_repo
        self._peer_client = peer_client
        self._validator = validator

    async def execute(self) -> bool:
        """Adopts the longest valid peer chain if it is longer than ours; True when ours was replaced."""
        nodes = await self._node_repo.get_all()
        # The whole local chain, not one page of it
        max_length = await self._block_repo.count()
        new_chain: list[dict[str, Any]] | None = None

        for node in nodes:
            chain = await self._peer_client.fetch_chain(node.url)
            # The length is what was fetched, never the total a peer claims
            if chain is None or len(chain) <= max_length:
                continue
            reason = self._validator.violation(chain)
            if reason:
                logger.warning("Refused the chain of %s: %s", node.url, reason)
                continue
            max_length = len(chain)
            new_chain = chain

        if new_chain:
            await self._block_repo.replace_chain(new_chain)
            return True

        return False
