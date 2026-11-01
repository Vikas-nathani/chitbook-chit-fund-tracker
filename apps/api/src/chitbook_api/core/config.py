"""Application settings.

Every value comes from the environment (`.env` via docker compose). There are no defaults:
a missing variable stops the app at startup with a clear error.
"""

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    app_env: str
    tz: str = Field(alias="TZ")

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: SecretStr
    db_pool_size: int
    db_pool_max_overflow: int

    api_docs_enabled: bool
    cors_allowed_origins: str

    jwt_secret: SecretStr
    jwt_issuer: str
    access_token_ttl_minutes: int
    refresh_token_ttl_days: int
    refresh_cookie_secure: bool
    login_max_failed_attempts: int
    login_lockout_base_minutes: int
    login_lockout_max_minutes: int
    rate_limit_auth_per_minute: int

    admin_username: str
    admin_password: SecretStr
    admin_name: str
    admin_email: str

    log_level: str

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.tz)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
