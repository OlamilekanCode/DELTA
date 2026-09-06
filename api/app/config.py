from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    cors_origins: str = "http://localhost:3000"
    session_secret: str = "change-me-to-a-random-64-char-string"

    marketstack_api_key: str = ""
    coingecko_api_key: str = ""
    coingecko_api_type: str = "demo"  # "demo" | "pro"
    use_demo_data: bool = True

    delta_chain_id: int = 8453
    delta_token_address: str = ""
    delta_min_balance: str = ""
    alchemy_api_key: str = ""

    cron_secret: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
