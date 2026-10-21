import importlib
import pkgutil
from typing import Any, get_args, get_origin

from fastapi import APIRouter
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from pydantic import BaseModel

from backend.app.domain.entities.user import UserRole
from backend.app.infrastructure.database import get_db_session
from backend.app.main import app
from backend.app.presentation import api
from backend.app.presentation.dependencies.auth import RequireRole, get_current_user

ANY_ROLE = frozenset(UserRole)
TRADER_OR_ADMIN = frozenset({UserRole.TRADER, UserRole.ADMIN})
ADMIN = frozenset({UserRole.ADMIN})

# SPEC › API contract and › Permissions by role, one entry per route; None is public.
# A route missing from this table, or an entry with no route, fails.
ACCESS: dict[str, frozenset[UserRole] | None] = {
    "GET /health": None,
    "POST /auth/login": None,
    "GET /auth/me": ANY_ROLE,
    "POST /users": ADMIN,
    "POST /wallets/generate": None,
    "GET /wallets/{address}/balance": None,
    "POST /transactions": ANY_ROLE,
    "GET /transactions/{tx_hash}": ANY_ROLE,
    "GET /blocks": ANY_ROLE,
    "GET /blocks/full": ANY_ROLE,
    "GET /blocks/{block_hash}": ANY_ROLE,
    "POST /blocks/mine": TRADER_OR_ADMIN,
    "POST /nodes/register": ADMIN,
    "GET /nodes": ANY_ROLE,
    "POST /nodes/resolve": ADMIN,
}

# Public routes that may be other than GET: signing in, and a key pair that writes nothing
PUBLIC_NON_GET = {"POST /auth/login", "POST /auth/demo", "POST /wallets/generate"}

# Known debt, one entry per route: any signed-in user can call them today. VLA-19 adds the roles.
KNOWN_ROLE_VIOLATIONS = {"POST /blocks/mine", "POST /nodes/register", "POST /nodes/resolve"}


def all_routes() -> dict[str, APIRoute]:
    # FastAPI keeps included routers as private objects in app.routes, so every router module is read instead
    routers = [app.router]
    for module_info in pkgutil.iter_modules(api.__path__):
        module = importlib.import_module(f"{api.__name__}.{module_info.name}")
        routers += [obj for obj in vars(module).values() if isinstance(obj, APIRouter)]
    routes = {}
    for router in routers:
        for route in router.routes:
            if isinstance(route, APIRoute):
                for method in sorted(route.methods or ()):
                    routes[f"{method} {route.path}"] = route
    assert routes, "no routes found; the walk is broken"
    return routes


def dependencies(dependant: Dependant) -> list[Dependant]:
    found = []
    for sub in dependant.dependencies:
        found.append(sub)
        found.extend(dependencies(sub))
    return found


def is_signed_in(route: APIRoute) -> bool:
    return any(dep.call is get_current_user for dep in dependencies(route.dependant))


def roles(route: APIRoute) -> frozenset[UserRole] | None:
    required = [
        frozenset(dep.call.allowed_roles) for dep in dependencies(route.dependant) if isinstance(dep.call, RequireRole)
    ]
    if required:
        return frozenset.intersection(*required)
    return ANY_ROLE if is_signed_in(route) else None


def is_model(annotation: Any) -> bool:
    if get_origin(annotation) is list:
        return is_model(get_args(annotation)[0])
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def test_ar08_every_route_requires_a_token_unless_it_is_public() -> None:
    routes = all_routes()
    assert set(routes) == set(ACCESS)
    public = {name for name, route in routes.items() if not is_signed_in(route)}
    assert public == {name for name, access in ACCESS.items() if access is None}
    assert {name for name in public if not name.startswith("GET ")} <= PUBLIC_NON_GET


def test_ar09_every_route_requires_the_roles_of_the_spec() -> None:
    routes = all_routes()
    assert set(routes) == set(ACCESS)
    assert {name for name, route in routes.items() if roles(route) != ACCESS[name]} == KNOWN_ROLE_VIOLATIONS


def test_ar10_every_route_declares_a_pydantic_response_model() -> None:
    assert {name for name, route in all_routes().items() if not is_model(route.response_model)} == set()


def test_ar16_every_route_commits_before_the_response() -> None:
    # A plain Depends(get_db_session) would commit after the response is sent and open a second session
    scopes = {
        name: [dep.scope for dep in dependencies(route.dependant) if dep.call is get_db_session]
        for name, route in all_routes().items()
    }
    assert any(scopes.values()), "no route uses the session; the walk is broken"
    wrong = {name: found for name, found in scopes.items() if any(scope != "function" for scope in found)}
    assert wrong == {}, "use DbSession from presentation/dependencies/database.py"
