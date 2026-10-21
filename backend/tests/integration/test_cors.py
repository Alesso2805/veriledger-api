import os
import subprocess
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient

from backend.app.core.config import settings

pytestmark = pytest.mark.asyncio

ROOT = Path(__file__).resolve().parents[3]


def preflight(origin: str) -> dict[str, str]:
    return {
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization",
    }


async def test_a_configured_origin_may_call_the_api_from_a_browser(async_client: AsyncClient) -> None:
    origin = settings.cors_origin_list[0]

    response = await async_client.options("/transactions", headers=preflight(origin))

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


async def test_any_other_origin_is_not_allowed(async_client: AsyncClient) -> None:
    response = await async_client.options("/transactions", headers=preflight("https://elsewhere.example"))

    assert "access-control-allow-origin" not in response.headers


def test_the_middleware_takes_its_origins_from_cors_origins() -> None:
    # A fresh interpreter, since the middleware is built when main is imported
    code = "from backend.app.main import app; print([m.kwargs.get('allow_origins') for m in app.user_middleware])"
    env = {**os.environ, "CORS_ORIGINS": "http://ci.example:4173,http://localhost:4173"}
    run = subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True)

    assert "['http://ci.example:4173', 'http://localhost:4173']" in run.stdout
