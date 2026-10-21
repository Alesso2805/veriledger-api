from abc import ABC, abstractmethod

from backend.app.domain.entities.node import Node


class NodeRepository(ABC):
    @abstractmethod
    async def create(self, node: Node) -> Node:
        pass

    @abstractmethod
    async def get_by_url(self, url: str) -> Node | None:
        pass

    @abstractmethod
    async def get_all(self) -> list[Node]:
        pass
