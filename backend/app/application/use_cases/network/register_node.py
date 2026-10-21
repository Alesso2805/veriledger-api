import uuid

from backend.app.application.dto.node import NodeCreateRequestDTO
from backend.app.domain.entities.node import Node
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.domain.ports.services.peer_url_policy import PeerUrlPolicy


class RegisterNodeUseCase:
    def __init__(self, node_repo: NodeRepository, url_policy: PeerUrlPolicy):
        self._node_repo = node_repo
        self._url_policy = url_policy

    async def execute(self, request: NodeCreateRequestDTO) -> Node:
        await self._url_policy.check(request.url)
        existing = await self._node_repo.get_by_url(request.url)
        if existing:
            raise ValueError("Node already registered")

        node = Node(
            id=str(uuid.uuid4()),
            url=request.url,
            status="ACTIVE",
        )
        return await self._node_repo.create(node)
