from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_debug: bool = True
    database_url: str

    secret_key: str = "supersecretkey"  # Development default; VLA-21 makes production refuse it
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Opens POST /auth/demo to anyone (ADR-0006); a node without it answers 404 there
    demo_mode: bool = False
    # ADR-0006's limits on the public demo; 0 turns one off, as the webapp's end-to-end CI needs
    demo_accounts_per_ip_per_hour: int = Field(default=5, ge=0)
    demo_max_active_accounts: int = Field(default=500, ge=0)
    demo_mines_per_hour: int = Field(default=10, ge=0)

    # The nodes of one network need the same values, since a peer's blocks are checked against ours (VLA-18).
    # A SHA-256 hex digest has 64 characters, so no hash meets a higher difficulty
    mining_difficulty: int = Field(default=4, ge=1, le=64)
    mining_reward: float = Field(default=50.0, ge=0)

    # Shared by the nodes of one network (VLA-19); unset or empty, no call is taken for a peer's
    peer_token: str | None = None
    # Lets peers sit on loopback, private and link-local addresses: development and private networks only
    allow_private_peers: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
