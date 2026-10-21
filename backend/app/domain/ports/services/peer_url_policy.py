from abc import ABC, abstractmethod


class PeerUrlPolicy(ABC):
    @abstractmethod
    async def check(self, url: str) -> None:
        """Raises UnsafePeerUrlError if this node must not call the URL (SPEC › Peer URLs)."""
