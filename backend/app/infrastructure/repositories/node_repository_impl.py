from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.domain.entities.node import Node
from backend.app.domain.ports.repositories.node_repository import NodeRepository
from backend.app.infrastructure.models.node_model import NodeModel

class NodeRepositoryImpl(NodeRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, node: Node) -> Node:
        model = NodeModel(
            id=node.id,
            url=node.url,
            status=node.status
        )
        self._session.add(model)
        await self._session.commit()
        return node

    async def get_by_url(self, url: str) -> Optional[Node]:
        stmt = select(NodeModel).where(NodeModel.url == url)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return Node(id=model.id, url=model.url, status=model.status)

    async def get_all(self) -> list[Node]:
        stmt = select(NodeModel)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [Node(id=m.id, url=m.url, status=m.status) for m in models]
