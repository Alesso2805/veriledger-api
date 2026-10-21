from abc import ABC, abstractmethod
from typing import Any


class PeerClient(ABC):
    @abstractmethod
    async def send_transaction(self, peer_urls: list[str], transaction: dict[str, Any]) -> None:
        """Offers a signed transaction to every peer; a peer that fails is skipped."""

    @abstractmethod
    async def request_resolve(self, peer_urls: list[str]) -> None:
        """Asks every peer to resolve conflicts, so that it fetches our new chain; a peer that fails is skipped."""

    @abstractmethod
    async def fetch_chain(self, peer_url: str) -> list[dict[str, Any]] | None:
        """A peer's whole chain as /blocks/full serializes it, newest first, or None if it cannot be read."""
