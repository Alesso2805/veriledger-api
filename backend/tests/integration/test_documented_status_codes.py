from collections import defaultdict
from pathlib import Path

import pytest
from starlette.routing import Match

from backend.tests.architecture.test_routes import all_routes
from backend.tests.conftest import RESPONSES
from backend.tests.integration.conftest import TEST_DATABASE_URL

# SPEC › API contract: every status code each route documents. The integration suite must produce each of them.
DOCUMENTED: dict[str, set[int]] = {
    "GET /health": {200},
    "POST /auth/login": {200, 401},
    "POST /auth/demo": {201, 404, 429},
    "GET /auth/me": {200, 401},
    "POST /users": {201, 400, 401, 403},
    "POST /wallets/generate": {200, 404},
    "GET /wallets/{address}/balance": {200},
    "GET /wallets/{address}/nonce": {200},
    "GET /wallets/{address}/transactions": {200, 422},
    "POST /transactions": {200, 201, 400, 401, 409, 422},
    "GET /transactions": {200, 422},
    "GET /transactions/{tx_hash}": {200, 404},
    "GET /blocks": {200, 422},
    "GET /blocks/full": {200, 422},
    "GET /blocks/{block_hash}": {200, 404},
    "POST /blocks/mine": {200, 401, 403, 409, 429},
    "POST /nodes/register": {201, 400, 401, 403},
    "GET /nodes": {200},
    "POST /nodes/resolve": {200, 401, 403},
}


def route_of(method: str, path: str) -> str | None:
    for name, route in all_routes().items():
        if (
            name.startswith(f"{method} ")
            and route.matches({"type": "http", "path": path, "method": method})[0] == Match.FULL
        ):
            return name
    return None


def test_every_route_lists_its_documented_status_codes() -> None:
    assert set(DOCUMENTED) == set(all_routes())


def test_every_documented_status_code_was_produced(request: pytest.FixtureRequest) -> None:
    if not TEST_DATABASE_URL.startswith("postgresql"):
        pytest.skip("needs the integration suite on PostgreSQL")
    modules = {path.name for path in Path(__file__).parent.glob("test_*.py")}
    collected = {item.path.name for item in request.session.items}
    if not modules <= collected or request.config.getoption("keyword") or request.config.getoption("markexpr"):
        pytest.skip("needs the whole integration suite in one run")

    produced: dict[str, set[int]] = defaultdict(set)
    for method, path, status in RESPONSES:
        if (name := route_of(method, path)) is not None:
            produced[name].add(status)

    missing = {name: sorted(codes - produced[name]) for name, codes in DOCUMENTED.items() if codes - produced[name]}
    assert missing == {}, "a documented status code has no test that produces it"
