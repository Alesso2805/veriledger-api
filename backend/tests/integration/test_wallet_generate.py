import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from httpx import AsyncClient

from backend.app.core.config import settings

pytestmark = pytest.mark.asyncio


async def test_generate_answers_a_key_pair_that_signs_and_verifies(async_client: AsyncClient) -> None:
    # Development only (SPEC › API contract); the webapp makes its keys in the browser
    response = await async_client.post("/wallets/generate")
    pair = response.json()

    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(pair["private_key"]))
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pair["public_key"]))
    public_key.verify(private_key.sign(b"message"), b"message")
    assert response.status_code == 200


async def test_generate_answers_404_outside_development(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The private key would cross the network, so only development has this helper (VLA-21)
    monkeypatch.setattr(settings, "app_env", "production")

    response = await async_client.post("/wallets/generate")

    assert (response.status_code, response.json()["detail"]) == (404, "Not Found")
