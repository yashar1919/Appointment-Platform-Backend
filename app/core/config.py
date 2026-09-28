from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Appointment Platform API"
    app_env: str = "development"
    debug: bool = False
    database_url: str
    database_sync_url: str
    cors_origins: str = "http://localhost:3000"
    admin_api_key: str = ""
    meli_payamak_username: str = ""
    meli_payamak_password: str = ""
    meli_payamak_from_number: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
