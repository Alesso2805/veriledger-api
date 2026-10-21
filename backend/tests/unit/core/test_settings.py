from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings

DATABASE_URL = "postgresql+asyncpg://user:password@db/veriledger"

UNSAFE_SECRET_KEYS = {
    "missing": None,
    "the example value": "supersecretkey_change_me_in_production",
    "under 32 bytes": "x" * 31,
}


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # No .env file and no SECRET_KEY from the machine running the tests
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SECRET_KEY", raising=False)


@pytest.mark.xfail(strict=True, reason="VLA-21: the settings do not validate SECRET_KEY in production yet")
@pytest.mark.parametrize("secret_key", UNSAFE_SECRET_KEYS.values(), ids=UNSAFE_SECRET_KEYS.keys())
def test_ar15_production_refuses_an_unsafe_secret_key(secret_key: str | None) -> None:
    with pytest.raises(ValidationError):
        if secret_key is None:
            Settings(app_env="production", database_url=DATABASE_URL)
        else:
            Settings(app_env="production", database_url=DATABASE_URL, secret_key=secret_key)


def test_production_accepts_a_long_random_secret_key() -> None:
    settings = Settings(app_env="production", database_url=DATABASE_URL, secret_key="k" * 48)
    assert settings.app_env == "production"
