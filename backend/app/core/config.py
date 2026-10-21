from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_debug: bool = True
    database_url: str

    secret_key: str = "supersecretkey"  # Development default; VLA-21 makes production refuse it
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Shared by the nodes of one network (VLA-19); unset or empty, no call is taken for a peer's
    peer_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
