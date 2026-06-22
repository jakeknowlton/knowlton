from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 90
    database_url: str = "sqlite:///./app.db"

    # The single origin allowed to make credentialed (cookie-bearing) requests.
    # CORS with credentials forbids a "*" wildcard, so the exact frontend origin
    # must be named here — it differs between dev and each deployment.
    frontend_origin: str = "http://localhost:5173"


settings = Settings()  # type: ignore[call-arg]
