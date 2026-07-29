import uuid
from backend.app.application.dto.node import NodeCreateRequestDTO
from backend.app.domain.entities.node import Node
from backend.app.domain.ports.repositories.node_repository import NodeRepository


class RegisterNodeUseCase:
    def __init__(self, node_repo: NodeRepository):
        self._node_repo = node_repo

    async def execute(self, request: NodeCreateRequestDTO) -> Node:
        existing = await self._node_repo.get_by_url(request.url)
        if existing:
            raise ValueError("Node already registered")

        node = Node(
            id=str(uuid.uuid4()),
            url=request.url,
            status="ACTIVE",
        )
        return await self._node_repo.create(node)
