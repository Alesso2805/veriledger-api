import tomllib
from pathlib import Path

from backend.app.main import app

ROOT = Path(__file__).resolve().parents[3]


def test_the_app_the_changelog_and_pyproject_name_the_same_version() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

    assert app.version == version
    # The release a tag publishes has its entry in the changelog (VLA-30)
    assert f"## [{version}] - " in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
