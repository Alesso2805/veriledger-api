import asyncio
from typing import Any

import httpx
import structlog

from backend.app.core.config import MAX_PAGE_SIZE, settings
from backend.app.domain.errors import UnsafePeerUrlError
from backend.app.domain.ports.services.peer_client import PeerClient
from backend.app.domain.ports.services.peer_url_policy import PeerUrlPolicy
from backend.app.infrastructure.peers.resolving_peer_url_policy import ResolvingPeerUrlPolicy

logger = structlog.get_logger()


class HttpxPeerClient(PeerClient):
    def __init__(
        self,
        timeout: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
        peer_token: str | None = None,
        url_policy: PeerUrlPolicy | None = None,
    ):
        self._timeout = timeout
        self._transport = transport
        token = peer_token if peer_token is not None else settings.peer_token
        # Peers take it in place of a user on POST /transactions and /nodes/resolve
        self._headers = {"X-Peer-Token": token} if token else {}
        self._url_policy = url_policy or ResolvingPeerUrlPolicy()

    async def _callable(self, peer_urls: list[str]) -> list[str]:
        # Checked again before every call: a host can change its answer after it was registered
        allowed = []
        for url in peer_urls:
            try:
                await self._url_policy.check(url)
            except UnsafePeerUrlError as e:
                logger.warning("Skipping a peer this node must not call", url=url, reason=str(e))
                continue
            allowed.append(url)
        return allowed

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout, transport=self._transport, headers=self._headers)

    async def send_transaction(self, peer_urls: list[str], transaction: dict[str, Any]) -> None:
        urls = await self._callable(peer_urls)
        async with self._client() as client:
            calls = [client.post(f"{url}/transactions", json=transaction) for url in urls]
            await asyncio.gather(*calls, return_exceptions=True)

    async def request_resolve(self, peer_urls: list[str]) -> None:
        urls = await self._callable(peer_urls)
        async with self._client() as client:
            await asyncio.gather(*[client.post(f"{url}/nodes/resolve") for url in urls], return_exceptions=True)

    async def fetch_chain(self, peer_url: str) -> list[dict[str, Any]] | None:
        if not await self._callable([peer_url]):
            return None
        # Every page: one page would cut a longer chain to its newest blocks
        blocks: list[dict[str, Any]] = []
        total: int | None = None
        try:
            async with self._client() as client:
                while True:
                    params = {"skip": len(blocks), "limit": MAX_PAGE_SIZE}
                    response = await client.get(f"{peer_url}/blocks/full", params=params)
                    if response.status_code != 200:
                        return None
                    page = response.json()
                    blocks += page["items"]
                    # The first page's total bounds the walk, so a peer cannot keep it going
                    total = page["total"] if total is None else total
                    if len(page["items"]) < MAX_PAGE_SIZE or len(blocks) >= total:
                        return blocks
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return None
