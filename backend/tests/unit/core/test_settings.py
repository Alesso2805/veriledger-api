from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings

DATABASE_URL = "postgresql+asyncpg://user:password@db/veriledger"

UNSAFE_SECRET_KEYS = {
    "missing": None,
    "the development default": "supersecretkey",
    "empty": "",
    "the example value": "supersecretkey_change_me_in_production",
    "under 32 bytes": "x" * 31,
}


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # No .env file and no SECRET_KEY from the machine running the tests
    monkeypatch.chdir(tmp_path)
    for name in ("SECRET_KEY", "APP_ENV", "APP_DEBUG", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("secret_key", UNSAFE_SECRET_KEYS.values(), ids=UNSAFE_SECRET_KEYS.keys())
def test_ar15_production_refuses_an_unsafe_secret_key(secret_key: str | None) -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY must be set in production"):
        if secret_key is None:
            Settings(app_env="production", database_url=DATABASE_URL)
        else:
            Settings(app_env="production", database_url=DATABASE_URL, secret_key=secret_key)


def test_production_accepts_a_long_random_secret_key() -> None:
    settings = Settings(app_env="production", database_url=DATABASE_URL, secret_key="k" * 48)
    assert settings.app_env == "production"


def test_mining_defaults_to_difficulty_4_and_a_reward_of_50(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINING_DIFFICULTY", raising=False)
    monkeypatch.delenv("MINING_REWARD", raising=False)
    settings = Settings(database_url=DATABASE_URL)
    assert (settings.mining_difficulty, settings.mining_reward) == (4, 50.0)


def test_mining_reads_its_settings_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINING_DIFFICULTY", "5")
    monkeypatch.setenv("MINING_REWARD", "12.5")
    settings = Settings(database_url=DATABASE_URL)
    assert (settings.mining_difficulty, settings.mining_reward) == (5, 12.5)


@pytest.mark.parametrize(
    "overrides",
    [{"mining_difficulty": 0}, {"mining_difficulty": 65}, {"mining_reward": -1}],
    ids=["no difficulty", "more zeros than a hash has", "negative reward"],
)
def test_mining_settings_out_of_range_are_refused(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Settings(database_url=DATABASE_URL, **overrides)


def test_the_demo_limits_default_to_adr_0006s(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DEMO_ACCOUNTS_PER_IP_PER_HOUR", "DEMO_MAX_ACTIVE_ACCOUNTS", "DEMO_MINES_PER_HOUR"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(database_url=DATABASE_URL)
    assert (
        settings.demo_accounts_per_ip_per_hour,
        settings.demo_max_active_accounts,
        settings.demo_mines_per_hour,
    ) == (
        5,
        500,
        10,
    )


@pytest.mark.parametrize("name", ["demo_accounts_per_ip_per_hour", "demo_max_active_accounts", "demo_mines_per_hour"])
def test_a_negative_demo_limit_is_refused(name: str) -> None:
    overrides: dict[str, Any] = {name: -1}
    with pytest.raises(ValidationError):
        Settings(database_url=DATABASE_URL, **overrides)


def test_development_keeps_its_default_secret_key() -> None:
    assert Settings(database_url=DATABASE_URL).secret_key == "supersecretkey"


def test_debug_is_off_unless_asked_for(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings(database_url=DATABASE_URL).app_debug is False
    monkeypatch.setenv("APP_DEBUG", "true")
    assert Settings(database_url=DATABASE_URL).app_debug is True


def test_cors_origins_are_a_comma_separated_list(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings(database_url=DATABASE_URL).cors_origin_list == ["http://localhost:5173", "http://127.0.0.1:5173"]
    monkeypatch.setenv("CORS_ORIGINS", " http://127.0.0.1:4173, http://localhost:4173 ,")
    assert Settings(database_url=DATABASE_URL).cors_origin_list == ["http://127.0.0.1:4173", "http://localhost:4173"]
