import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio


async def signed_in_as(client: AsyncClient, admin_headers: dict[str, str], role: str) -> dict[str, str]:
    email = f"{role}@example.com"
    created = await client.post(
        "/users", json={"email": email, "password": "a-password", "role": role}, headers=admin_headers
    )
    assert created.status_code == 201
    login = await client.post("/auth/login", data={"username": email, "password": "a-password"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# SPEC › Permissions by role: mining for traders and admins, peers for admins only
@pytest.mark.parametrize(
    ("role", "expected"),
    [("viewer", (403, 403, 403)), ("trader", (200, 403, 403)), ("admin", (200, 201, 200))],
)
async def test_each_role_mines_and_manages_peers_as_the_spec_says(
    async_client: AsyncClient,
    postgres: async_sessionmaker[AsyncSession],
    admin_headers: dict[str, str],
    private_peers: None,
    role: str,
    expected: tuple[int, int, int],
) -> None:
    headers = admin_headers if role == "admin" else await signed_in_as(async_client, admin_headers, role)

    mined = await async_client.post("/blocks/mine", json={"miner_address": "miner"}, headers=headers)
    registered = await async_client.post("/nodes/register", json={"url": f"http://{role}.example"}, headers=headers)
    resolved = await async_client.post("/nodes/resolve", headers=headers)

    assert (mined.status_code, registered.status_code, resolved.status_code) == expected


async def test_only_an_admin_creates_users(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession], admin_headers: dict[str, str]
) -> None:
    headers = await signed_in_as(async_client, admin_headers, "trader")

    response = await async_client.post(
        "/users", json={"email": "another@example.com", "password": "a-password", "role": "viewer"}, headers=headers
    )

    assert response.status_code == 403
