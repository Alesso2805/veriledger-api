import importlib
import pkgutil

from fastapi import APIRouter
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from backend.app.infrastructure.database import get_db_session
from backend.app.main import app
from backend.app.presentation import api


def all_routes() -> list[APIRoute]:
    # FastAPI keeps included routers as private objects in app.routes, so every router module is read instead
    routers = [app.router]
    for module_info in pkgutil.iter_modules(api.__path__):
        module = importlib.import_module(f"{api.__name__}.{module_info.name}")
        routers += [obj for obj in vars(module).values() if isinstance(obj, APIRouter)]
    return [route for router in routers for route in router.routes if isinstance(route, APIRoute)]


def session_scopes(dependant: Dependant) -> list[str | None]:
    scopes: list[str | None] = []
    for sub in dependant.dependencies:
        if sub.call is get_db_session:
            scopes.append(sub.scope)
        scopes.extend(session_scopes(sub))
    return scopes


def test_every_route_commits_before_the_response() -> None:
    # A plain Depends(get_db_session) would commit after the response is sent and open a second session
    scopes_by_route = {
        f"{sorted(route.methods or ())} {route.path}": session_scopes(route.dependant) for route in all_routes()
    }

    assert any(scopes_by_route.values()), "no route uses the session; the walk is broken"
    wrong = {route: scopes for route, scopes in scopes_by_route.items() if any(s != "function" for s in scopes)}
    assert wrong == {}, "use DbSession from presentation/dependencies/database.py"
