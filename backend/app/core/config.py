from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_SECRET_KEY = "supersecretkey"
# The value .env.example ships, which anyone can read
EXAMPLE_SECRET_KEY = "supersecretkey_change_me_in_production"
MIN_SECRET_KEY_BYTES = 32
# The seed's development password, which production refuses
DEVELOPMENT_ADMIN_PASSWORD = "adminpassword123"
# ADR-0006 caps every page of a public read at this size; peers page through each other's chains at it
MAX_PAGE_SIZE = 100


class Settings(BaseSettings):
    app_env: str = "development"
    # Off unless asked for: it echoes every SQL statement
    app_debug: bool = False
    database_url: str

    # Development only: production refuses it
    secret_key: str = DEVELOPMENT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # The admin the seed creates once; production refuses the development password
    admin_email: str = "admin@veriledger.com"
    admin_password: str = DEVELOPMENT_ADMIN_PASSWORD

    # Comma-separated browser origins allowed to call the API; behind Caddy the webapp shares its origin (ADR-0005)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # The prefix a proxy strips before the API sees the path, /api behind Caddy; /docs needs it
    api_root_path: str = ""

    # Opens POST /auth/demo to anyone (ADR-0006); a node without it answers 404 there
    demo_mode: bool = False
    # ADR-0006's limits on the public demo; 0 turns one off, as the webapp's end-to-end CI needs
    demo_accounts_per_ip_per_hour: int = Field(default=5, ge=0)
    demo_max_active_accounts: int = Field(default=500, ge=0)
    demo_mines_per_hour: int = Field(default=10, ge=0)
    # Abuse limits on every node; 0 or false turns one off
    login_attempts_per_minute: int = Field(default=5, ge=0)
    transactions_per_sender_per_minute: int = Field(default=60, ge=0)
    mine_one_at_a_time: bool = True

    # The nodes of one network need the same values, since a peer's blocks are checked against ours.
    # A SHA-256 hex digest has 64 characters, so no hash meets a higher difficulty
    mining_difficulty: int = Field(default=4, ge=1, le=64)
    mining_reward: float = Field(default=50.0, ge=0)

    # Shared by the nodes of one network; unset or empty, no call is accepted as a peer's
    peer_token: str | None = None
    # Lets peers sit on loopback, private and link-local addresses: development and private networks only
    allow_private_peers: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def refuse_an_unsafe_secret_key_in_production(self) -> Self:
        # Anyone who knows the key signs tokens for any user, so production does not start with a guessable one
        if self.app_env == "production" and (
            self.secret_key in (DEVELOPMENT_SECRET_KEY, EXAMPLE_SECRET_KEY)
            or len(self.secret_key.encode("utf-8")) < MIN_SECRET_KEY_BYTES
        ):
            raise ValueError(
                f"SECRET_KEY must be set in production to at least {MIN_SECRET_KEY_BYTES} random bytes; "
                "the development default and the example value are refused"
            )
        return self


settings = Settings()
