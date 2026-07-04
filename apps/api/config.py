from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(env_file=".env")

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 90
    database_url: str = "sqlite:///./app.db"

    # The single origin allowed to make credentialed (cookie-bearing) requests.
    # CORS with credentials forbids a "*" wildcard, so the exact frontend origin
    # must be named here — it differs between dev and each deployment.
    frontend_origin: str = "http://localhost:5173"


# `secret_key` has no default by design (fail-fast if unset); pydantic-settings
# populates it from the environment / `.env` at runtime, which the type checker
# can't see, so it reads the constructor as missing a required argument.
settings = Settings()  # pyright: ignore[reportCallIssue]
