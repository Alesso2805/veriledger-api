import asyncio
import os
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from functools import partial
from pathlib import Path
from typing import IO

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.domain.entities.user import UserRole
from backend.app.infrastructure.database import Base
from backend.app.infrastructure.models.user import UserModel
from backend.app.infrastructure.security.password_hasher import PasswordHasherImpl
from backend.tests.integration.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, TEST_DATABASE_URL, VECTORS, fund, submit

pytestmark = pytest.mark.asyncio

ROOT = Path(__file__).resolve().parents[3]
PEER_TOKEN = "shared-by-both-nodes"
BY_NAME = {vector["name"]: vector for vector in VECTORS}


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


async def on_server(statement: str) -> None:
    # CREATE and DROP DATABASE cannot run inside a transaction
    server = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, isolation_level="AUTOCOMMIT")
    async with server.connect() as conn:
        await conn.execute(text(statement))
    await server.dispose()


async def create_database(name: str) -> str:
    await on_server(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    await on_server(f'CREATE DATABASE "{name}"')
    url = make_url(TEST_DATABASE_URL).set(database=name).render_as_string(hide_password=False)
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine)() as session:
        session.add(
            UserModel(
                id=str(uuid.uuid4()),
                email=ADMIN_EMAIL,
                password_hash=PasswordHasherImpl().hash_password(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
            )
        )
        await session.commit()
    await engine.dispose()
    return url


async def wait_until_up(url: str, process: subprocess.Popen[bytes], log: Path) -> None:
    deadline = time.monotonic() + 30
    async with httpx.AsyncClient() as client:
        while True:
            if process.poll() is not None:
                pytest.fail(f"the node at {url} exited:\n{log.read_text(errors='replace')}")
            try:
                if (await client.get(f"{url}/health")).status_code == 200:
                    return
            except httpx.TransportError:
                pass
            if time.monotonic() > deadline:
                pytest.fail(f"the node at {url} did not start")
            await asyncio.sleep(0.2)


@pytest_asyncio.fixture
async def nodes(tmp_path: Path) -> AsyncGenerator[tuple[str, str], None]:
    """Two API processes, each with its own database, sharing PEER_TOKEN."""
    if not TEST_DATABASE_URL.startswith("postgresql"):
        pytest.skip("needs TEST_DATABASE_URL pointing to a throwaway PostgreSQL")

    names = [f"{make_url(TEST_DATABASE_URL).database}_node_{node}" for node in ("a", "b")]
    started: list[tuple[subprocess.Popen[bytes], IO[bytes], Path]] = []
    try:
        urls = []
        for name in names:
            env = {
                **os.environ,
                "DATABASE_URL": await create_database(name),
                "PEER_TOKEN": PEER_TOKEN,
                "APP_DEBUG": "false",
                "ALLOW_PRIVATE_PEERS": "true",
            }
            port = free_port()
            log = tmp_path / f"{name}.log"
            log_file = log.open("wb")
            command = [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ]
            started.append(
                (subprocess.Popen(command, cwd=ROOT, env=env, stdout=log_file, stderr=subprocess.STDOUT), log_file, log)
            )
            urls.append(f"http://127.0.0.1:{port}")
        for (process, _, log), url in zip(started, urls, strict=True):
            await wait_until_up(url, process, log)
        yield urls[0], urls[1]
    finally:
        for process, output, log in started:
            process.terminate()
            process.wait(timeout=10)
            output.close()
            # pytest shows it only when the test fails
            print(f"--- {log.name}\n{log.read_text(errors='replace')}")
        for name in names:
            await on_server(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


async def sign_in(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def balance(client: httpx.AsyncClient, address: str) -> float:
    return float((await client.get(f"/wallets/{address}/balance")).json()["balance"])


async def status(client: httpx.AsyncClient, tx_hash: str) -> str | None:
    response = await client.get(f"/transactions/{tx_hash}")
    return str(response.json()["status"]) if response.status_code == 200 else None


async def eventually(read: Callable[[], Awaitable[object]], expected: object) -> None:
    # Peers hear of new data from background tasks that run after each response
    deadline = time.monotonic() + 15
    while (found := await read()) != expected:
        if time.monotonic() > deadline:
            pytest.fail(f"expected {expected!r}, still {found!r}")
        await asyncio.sleep(0.2)


async def test_a_transaction_and_the_block_that_confirms_it_reach_the_other_node(nodes: tuple[str, str]) -> None:
    a, b = nodes
    transfer, notarization = BY_NAME["transfer"], BY_NAME["notarization"]
    sender = transfer["fields"]["sender_address"]
    async with httpx.AsyncClient(base_url=a, timeout=10) as node_a, httpx.AsyncClient(base_url=b, timeout=10) as node_b:
        on_a, on_b = await sign_in(node_a), await sign_in(node_b)
        assert (await node_a.post("/nodes/register", json={"url": b}, headers=on_a)).status_code == 201
        assert (await node_b.post("/nodes/register", json={"url": a}, headers=on_b)).status_code == 201

        # Mining on A asks B to resolve, and B adopts A's chain with the sender's reward in it
        await fund(node_a, on_a, sender)
        await eventually(partial(balance, node_b, sender), 50.0)

        # Sent to A, each transaction is offered to B with the peer token
        hashes = [await submit(node_a, on_a, vector) for vector in (transfer, notarization)]
        for tx_hash in hashes:
            await eventually(partial(status, node_b, tx_hash), "PENDING")

        # A mines them, and B takes the chain that confirms them in place of its pending copies
        await fund(node_a, on_a, sender)
        for tx_hash in hashes:
            await eventually(partial(status, node_b, tx_hash), "CONFIRMED")
        adopted = (await node_b.get(f"/transactions/{hashes[1]}")).json()
        assert (adopted["payload"], adopted["nonce"]) == (notarization["fields"]["payload"], 1)
        assert await balance(node_b, sender) == await balance(node_a, sender)
