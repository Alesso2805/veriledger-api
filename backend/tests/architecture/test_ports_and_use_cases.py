import ast
import importlib
import inspect
import pkgutil
from pathlib import Path

import backend.app
from backend.app.domain import ports

APP = Path(__file__).resolve().parents[2] / "app"
TESTS = Path(__file__).resolve().parents[1]


def import_all() -> None:
    # Subclasses only exist once their module is imported
    for info in pkgutil.walk_packages(backend.app.__path__, f"{backend.app.__name__}."):
        importlib.import_module(info.name)


def all_ports() -> list[type]:
    found = []
    for info in pkgutil.walk_packages(ports.__path__, f"{ports.__name__}."):
        module = importlib.import_module(info.name)
        found += [
            cls
            for _, cls in inspect.getmembers(module, inspect.isclass)
            if cls.__module__ == module.__name__ and inspect.isabstract(cls)
        ]
    assert found, "no ports found; the walk is broken"
    return found


def implementations(port: type) -> list[type]:
    found = []
    for sub in port.__subclasses__():
        if not inspect.isabstract(sub) and sub.__module__.startswith("backend.app.infrastructure."):
            found.append(sub)
        found += implementations(sub)
    return found


def test_ar11_every_port_has_an_implementation_and_repositories_follow_the_naming() -> None:
    import_all()
    problems = []
    for port in all_ports():
        found = implementations(port)
        if not found:
            problems.append(f"{port.__name__} has no implementation in infrastructure")
        if port.__module__.startswith(f"{ports.__name__}.repositories."):
            module = f"backend.app.infrastructure.repositories.{port.__module__.rsplit('.', 1)[1]}_impl"
            if not any(cls.__name__ == f"{port.__name__}Impl" and cls.__module__ == module for cls in found):
                problems.append(f"{port.__name__} is not implemented by {module}.{port.__name__}Impl")
    assert problems == []


def test_ar12_every_use_case_is_one_class_with_execute_and_a_test_file() -> None:
    files = sorted(path for path in (APP / "application" / "use_cases").rglob("*.py") if path.name != "__init__.py")
    assert files, "no use cases found; the walk is broken"
    problems = []
    for path in files:
        name = f"{path.parent.name}/{path.name}"
        classes = [node for node in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(node, ast.ClassDef)]
        if len(classes) != 1:
            problems.append(f"{name} defines {len(classes)} classes")
        elif not any(
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == "execute"
            for node in classes[0].body
        ):
            problems.append(f"{name} has no execute method")
        if not (TESTS / "unit" / "application" / "use_cases" / path.parent.name / f"test_{path.name}").is_file():
            problems.append(f"{name} has no unit test file")
    assert problems == []


def test_ar16_no_repository_or_use_case_commits() -> None:
    # The request's session dependency is the only place that commits (ADR-0007)
    files = [*(APP / "application").rglob("*.py"), *(APP / "infrastructure" / "repositories").rglob("*.py")]
    commits = sorted(
        f"{path.relative_to(APP).as_posix()}:{node.lineno}"
        for path in files
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "commit"
    )
    assert commits == []
