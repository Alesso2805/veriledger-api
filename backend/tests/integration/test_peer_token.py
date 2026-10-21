import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.core.config import settings
from backend.tests.integration.conftest import VECTORS, fund

pytestmark = pytest.mark.asyncio

TOKEN = "peer-token-for-tests"
TRANSFER = VECTORS[0]


@pytest.fixture
def as_peer(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setattr(settings, "peer_token", TOKEN)
    return {"X-Peer-Token": TOKEN}


async def test_a_peer_with_the_token_may_submit_and_resolve(
    async_client: AsyncClient, admin_headers: dict[str, str], as_peer: dict[str, str]
) -> None:
    await fund(async_client, admin_headers, TRANSFER["fields"]["sender_address"])
    body = {**TRANSFER["fields"], "signature": TRANSFER["signature"]}

    submitted = await async_client.post("/transactions", json=body, headers=as_peer)
    resolved = await async_client.post("/nodes/resolve", headers=as_peer)

    assert (submitted.status_code, resolved.status_code) == (201, 200)


@pytest.mark.parametrize(
    ("configured", "sent"),
    [(TOKEN, "a-wrong-token"), (TOKEN, TOKEN.upper()), (None, "anything"), ("", "")],
    ids=["wrong", "other case", "not configured", "configured empty"],
)
async def test_any_other_token_is_refused(
    async_client: AsyncClient,
    postgres: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    configured: str | None,
    sent: str,
) -> None:
    monkeypatch.setattr(settings, "peer_token", configured)

    response = await async_client.post("/nodes/resolve", headers={"X-Peer-Token": sent})

    assert response.status_code == 401


async def test_the_token_opens_no_other_write(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], as_peer: dict[str, str]
) -> None:
    mined = await async_client.post("/blocks/mine", json={"miner_address": "a" * 64}, headers=as_peer)
    registered = await async_client.post("/nodes/register", json={"url": "http://peer.example"}, headers=as_peer)

    assert (mined.status_code, registered.status_code) == (401, 401)


async def test_a_transaction_from_a_peer_is_still_checked_against_its_signature(
    async_client: AsyncClient, admin_headers: dict[str, str], as_peer: dict[str, str]
) -> None:
    await fund(async_client, admin_headers, TRANSFER["fields"]["sender_address"])
    forged = {**TRANSFER["fields"], "amount": "11.00000000", "signature": TRANSFER["signature"]}

    response = await async_client.post("/transactions", json=forged, headers=as_peer)

    assert response.status_code == 400
