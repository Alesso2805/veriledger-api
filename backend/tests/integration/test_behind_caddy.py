import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def app_in_a_fresh_interpreter(code: str, **env: str) -> str:
    # The app is built when main is imported, so its settings are read by a new process
    run = subprocess.run(
        [sys.executable, "-c", f"from backend.app.main import app; {code}"],
        env={**os.environ, **env},
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return run.stdout


def test_behind_the_api_prefix_the_docs_page_reads_the_document_through_it() -> None:
    code = (
        "from fastapi.testclient import TestClient; client = TestClient(app); "
        "print(client.get('/health').status_code, '/api/openapi.json' in client.get('/docs').text)"
    )

    # Caddy strips /api, so the path still routes; the docs page asks for /api/openapi.json
    assert app_in_a_fresh_interpreter(code, API_ROOT_PATH="/api").split()[-2:] == ["200", "True"]


def test_without_a_prefix_the_document_declares_no_server() -> None:
    assert "None" in app_in_a_fresh_interpreter("print(app.openapi().get('servers'))", API_ROOT_PATH="")
