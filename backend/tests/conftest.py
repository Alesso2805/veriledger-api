from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, Response

from backend.app.main import app

# Every (method, path, status) the in-process client received, for the documented-status test (VLA-25)
RESPONSES: list[tuple[str, str, int]] = []
DOCUMENTED_STATUS_TEST = "test_every_documented_status_code_was_produced"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # That test reads what every other test produced, so it runs after all of them
    items.sort(key=lambda item: item.name == DOCUMENTED_STATUS_TEST)


async def record(response: Response) -> None:
    RESPONSES.append((response.request.method, response.request.url.path, response.status_code))


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", event_hooks={"response": [record]}) as client:
        yield client
