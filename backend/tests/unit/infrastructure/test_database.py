from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app.infrastructure import database
from backend.app.infrastructure.database import Base, get_db_session
from backend.app.infrastructure.models.node_model import NodeModel


@pytest_asyncio.fixture
async def session_maker(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    # StaticPool keeps a single connection, so the in-memory database survives between sessions
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(database, "async_session_maker", maker)
    yield maker
    await engine.dispose()


@pytest.mark.asyncio
async def test_commits_when_the_endpoint_returns(session_maker: async_sessionmaker[AsyncSession]) -> None:
    sessions = get_db_session()
    session = await anext(sessions)
    session.add(NodeModel(id="node-1", url="http://peer"))

    with pytest.raises(StopAsyncIteration):
        await anext(sessions)

    async with session_maker() as check:
        assert await check.get(NodeModel, "node-1") is not None


@pytest.mark.asyncio
async def test_commits_nothing_when_the_endpoint_raises(session_maker: async_sessionmaker[AsyncSession]) -> None:
    sessions = get_db_session()
    session = await anext(sessions)
    session.add(NodeModel(id="node-1", url="http://peer"))
    await session.flush()

    # FastAPI throws the endpoint's exception into the dependency at its yield
    with pytest.raises(ValueError):
        await sessions.athrow(ValueError("the endpoint failed after writing"))

    async with session_maker() as check:
        assert await check.get(NodeModel, "node-1") is None
