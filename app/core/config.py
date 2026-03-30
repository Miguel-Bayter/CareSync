from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql://user:password@localhost/mimedicacion"
    secret_key: SecretStr = SecretStr("change-me-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    app_name: str = "CareSync API"
    environment: str = "production"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    gmail_user: str = ""
    gmail_app_password: SecretStr = SecretStr("")
    openfda_base_url: str = "https://api.fda.gov/drug/label.json"
    openfda_timeout_seconds: float = 15.0

    @property
    def is_development(self) -> bool:
        """Return True when running in development environment."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


settings = get_settings()
