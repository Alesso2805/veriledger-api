from typing import Any

import httpx
import pytest

from backend.app.core.config import settings
from backend.app.infrastructure.peers.httpx_peer_client import HttpxPeerClient
from backend.app.infrastructure.peers.resolving_peer_url_policy import ResolvingPeerUrlPolicy


@pytest.fixture(autouse=True)
def private_peers(monkeypatch: pytest.MonkeyPatch) -> None:
    # These peers are bare names like http://peer, which only ALLOW_PRIVATE_PEERS lets through
    monkeypatch.setattr(settings, "allow_private_peers", True)


def peer_with_chain(blocks: int, seen: list[httpx.Request]) -> httpx.MockTransport:
    chain = [{"block_hash": f"h{n}"} for n in range(blocks - 1, -1, -1)]  # newest first, like /blocks/full

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        skip, limit = int(request.url.params["skip"]), int(request.url.params["limit"])
        return httpx.Response(
            200, json={"items": chain[skip : skip + limit], "total": len(chain), "page": 1, "size": limit}
        )

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_a_chain_longer_than_a_page_is_read_whole_and_in_order() -> None:
    seen: list[httpx.Request] = []
    client = HttpxPeerClient(transport=peer_with_chain(250, seen))

    chain = await client.fetch_chain("http://peer")

    assert chain is not None
    assert [block["block_hash"] for block in chain] == [f"h{n}" for n in range(249, -1, -1)]
    assert [request.url.params["skip"] for request in seen] == ["0", "100", "200"]


@pytest.mark.asyncio
async def test_the_first_total_bounds_the_walk_even_if_a_peer_keeps_claiming_more() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        skip = int(request.url.params["skip"])
        items = [{"block_hash": f"b{skip + n}"} for n in range(100)]
        # It says 200 first, then claims more on every page, always with a full page
        total = 200 if len(seen) == 1 else 200 + len(seen) * 1000
        return httpx.Response(200, json={"items": items, "total": total})

    chain = await HttpxPeerClient(transport=httpx.MockTransport(handler)).fetch_chain("http://peer")

    assert chain is not None and len(chain) == 200
    assert len(seen) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer",
    [httpx.Response(500), httpx.Response(200, json={"unexpected": True}), httpx.ConnectError("refused")],
    ids=["server error", "unexpected body", "unreachable"],
)
async def test_a_chain_that_cannot_be_read_is_none(answer: Any) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if isinstance(answer, Exception):
            raise answer
        return answer  # type: ignore[no-any-return]

    assert await HttpxPeerClient(transport=httpx.MockTransport(handler)).fetch_chain("http://peer") is None


@pytest.mark.asyncio
async def test_a_failing_peer_does_not_stop_the_others() -> None:
    posted: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "down":
            raise httpx.ConnectError("refused")
        posted.append(f"{request.url.host}{request.url.path}")
        return httpx.Response(201)

    client = HttpxPeerClient(transport=httpx.MockTransport(handler))
    await client.send_transaction(["http://down", "http://up"], {"nonce": 1})
    await client.request_resolve(["http://up", "http://down"])

    assert posted == ["up/transactions", "up/nodes/resolve"]


def recording(seen: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"items": [], "total": 0})

    return httpx.MockTransport(handler)


async def every_call(client: HttpxPeerClient) -> None:
    await client.send_transaction(["http://peer"], {"nonce": 1})
    await client.request_resolve(["http://peer"])
    await client.fetch_chain("http://peer")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("configured", "given", "sent"),
    [(None, "given", "given"), ("from-settings", None, "from-settings"), (None, None, None), ("", None, None)],
    ids=["given", "from settings", "none", "empty"],
)
async def test_every_call_carries_the_peer_token_when_there_is_one(
    monkeypatch: pytest.MonkeyPatch, configured: str | None, given: str | None, sent: str | None
) -> None:
    monkeypatch.setattr(settings, "peer_token", configured)
    seen: list[httpx.Request] = []

    await every_call(HttpxPeerClient(transport=recording(seen), peer_token=given))

    assert [request.headers.get("X-Peer-Token") for request in seen] == [sent] * 3


@pytest.mark.asyncio
async def test_a_peer_that_is_not_a_public_address_is_never_called() -> None:
    async def resolve(host: str) -> list[str]:
        return {"public": ["93.184.215.14"], "internal": ["10.0.0.1"]}[host]

    seen: list[httpx.Request] = []
    policy = ResolvingPeerUrlPolicy(allow_private=False, resolve=resolve)
    client = HttpxPeerClient(transport=recording(seen), url_policy=policy)

    await client.send_transaction(["http://internal", "http://public"], {"nonce": 1})
    await client.request_resolve(["http://internal", "http://public"])
    chain = await client.fetch_chain("http://internal")

    assert chain is None
    assert [f"{request.url.host}{request.url.path}" for request in seen] == [
        "public/transactions",
        "public/nodes/resolve",
    ]
