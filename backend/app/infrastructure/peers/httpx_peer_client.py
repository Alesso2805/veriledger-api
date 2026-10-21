import asyncio
from typing import Any

import httpx

from backend.app.domain.ports.services.peer_client import PeerClient

# The largest page /blocks/full serves (ADR-0006)
PAGE_SIZE = 100


class HttpxPeerClient(PeerClient):
    def __init__(self, timeout: float = 5.0, transport: httpx.AsyncBaseTransport | None = None):
        self._timeout = timeout
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout, transport=self._transport)

    async def send_transaction(self, peer_urls: list[str], transaction: dict[str, Any]) -> None:
        # Peers require a JWT this call does not send, so the broadcast fails between
        # authenticated nodes until VLA-19 adds a peer token
        async with self._client() as client:
            calls = [client.post(f"{url}/transactions", json=transaction) for url in peer_urls]
            await asyncio.gather(*calls, return_exceptions=True)

    async def request_resolve(self, peer_urls: list[str]) -> None:
        async with self._client() as client:
            await asyncio.gather(*[client.post(f"{url}/nodes/resolve") for url in peer_urls], return_exceptions=True)

    async def fetch_chain(self, peer_url: str) -> list[dict[str, Any]] | None:
        # Every page: one page would cut a longer chain to its newest blocks
        blocks: list[dict[str, Any]] = []
        total: int | None = None
        try:
            async with self._client() as client:
                while True:
                    params = {"skip": len(blocks), "limit": PAGE_SIZE}
                    response = await client.get(f"{peer_url}/blocks/full", params=params)
                    if response.status_code != 200:
                        return None
                    page = response.json()
                    blocks += page["items"]
                    # The first page's total bounds the walk, so a peer cannot keep it going
                    total = page["total"] if total is None else total
                    if len(page["items"]) < PAGE_SIZE or len(blocks) >= total:
                        return blocks
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return None
