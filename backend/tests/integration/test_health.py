import re

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.infrastructure import database

pytestmark = pytest.mark.asyncio


async def test_health_answers_ok_while_the_database_answers(
    async_client: AsyncClient, postgres: async_sessionmaker[AsyncSession]
) -> None:
    response = await async_client.get("/health")

    assert response.status_code == 200
    assert (response.json()["status"], response.json()["database"]) == ("ok", "ok")


async def test_health_answers_503_when_the_database_does_not(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Nothing listens on port 1, so every connection is refused
    nowhere = create_async_engine("postgresql+asyncpg://user:password@127.0.0.1:1/veriledger", poolclass=NullPool)
    monkeypatch.setattr(database, "async_session_maker", async_sessionmaker(nowhere))

    response = await async_client.get("/health")

    assert response.status_code == 503
    assert (response.json()["status"], response.json()["database"]) == ("unavailable", "unreachable")
    await nowhere.dispose()


async def test_each_response_carries_a_fresh_request_id(async_client: AsyncClient) -> None:
    first, second = await async_client.get("/health"), await async_client.get("/health")

    assert re.fullmatch(r"[0-9a-f]{32}", first.headers["X-Request-ID"])
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


@pytest.mark.parametrize(
    ("sent", "kept"),
    [("trace-42.a_b", True), ("bad id", False), ("x" * 65, False), ("line" + chr(0x2028) + "break", False)],
    ids=["safe", "a space", "too long", "a line separator"],
)
async def test_a_callers_request_id_is_kept_only_when_safe_to_log(
    async_client: AsyncClient, sent: str, kept: bool
) -> None:
    # Sent as bytes: httpx sends a str header only when it is ASCII
    response = await async_client.get("/health", headers={b"X-Request-ID": sent.encode("utf-8")})

    assert (response.headers["X-Request-ID"] == sent) is kept


async def test_each_request_is_logged_once_with_its_id(async_client: AsyncClient) -> None:
    with capture_logs() as logs:
        response = await async_client.get("/health", headers={"X-Request-ID": "trace-7"})

    handled = [entry for entry in logs if entry["event"] == "Request handled"]
    assert handled == [
        {
            "event": "Request handled",
            "log_level": "info",
            "request_id": "trace-7",
            "method": "GET",
            "path": "/health",
            "status": response.status_code,
            "duration_ms": handled[0]["duration_ms"],
        }
    ]
