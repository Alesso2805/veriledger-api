import ast
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def violations(layer: str, allowed: tuple[str, ...]) -> set[str]:
    # An allowlist, not a denylist: a new third-party library in the layer fails too
    files = sorted((APP / layer).rglob("*.py"))
    assert files, f"no modules under {layer}; the walk is broken"
    found = set()
    for path in files:
        for module in imported_modules(path):
            if module.split(".")[0] in sys.stdlib_module_names:
                continue
            if any(module == name or module.startswith(f"{name}.") for name in allowed):
                continue
            found.add(f"{path.relative_to(APP).as_posix()} imports {module}")
    return found


def test_ar01_domain_imports_only_the_standard_library_and_itself() -> None:
    assert violations("domain", ("backend.app.domain",)) == set()


def test_ar02_application_imports_only_the_standard_library_pydantic_and_inner_layers() -> None:
    allowed = ("pydantic", "backend.app.domain", "backend.app.core", "backend.app.application")
    assert violations("application", allowed) == set()
