import json
from pathlib import Path
from typing import Any

from backend.app.main import app

# Next to main.py, not in cli: AR-05 keeps cli from importing presentation, which the app is built from
DOCUMENT = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"


def render(document: dict[str, Any]) -> str:
    # Sorted keys and a fixed indent: the same API always writes the same bytes, so a stale file shows as a diff
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export(path: Path = DOCUMENT) -> None:
    path.write_text(render(app.openapi()), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    export()
