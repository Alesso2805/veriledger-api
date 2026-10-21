import pytest
from httpx import AsyncClient

from backend.app.core.config import settings

pytestmark = pytest.mark.asyncio

# A public address written as an IP, so that no test depends on DNS
PUBLIC_PEER = "http://93.184.215.14:8000"


@pytest.fixture
def public_peers_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "allow_private_peers", False)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://93.184.215.14",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://10.0.0.5:8000",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]:8000",
        "http://[::ffff:127.0.0.1]:8000",
    ],
)
async def test_a_peer_url_that_points_inside_is_refused_and_not_stored(
    async_client: AsyncClient, admin_headers: dict[str, str], public_peers_only: None, url: str
) -> None:
    response = await async_client.post("/nodes/register", json={"url": url}, headers=admin_headers)

    assert response.status_code == 400
    assert response.json()["detail"].startswith(("A peer URL", "The peer's host"))
    assert (await async_client.get("/nodes")).json() == []


async def test_a_public_peer_is_registered(
    async_client: AsyncClient, admin_headers: dict[str, str], public_peers_only: None
) -> None:
    response = await async_client.post("/nodes/register", json={"url": PUBLIC_PEER}, headers=admin_headers)

    assert response.status_code == 201


async def test_allow_private_peers_lets_a_local_node_register_but_not_another_scheme(
    async_client: AsyncClient, admin_headers: dict[str, str], private_peers: None
) -> None:
    local = await async_client.post("/nodes/register", json={"url": "http://127.0.0.1:8001"}, headers=admin_headers)
    other = await async_client.post("/nodes/register", json={"url": "ftp://127.0.0.1"}, headers=admin_headers)

    assert (local.status_code, other.status_code) == (201, 400)
