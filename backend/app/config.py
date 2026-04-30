from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Mode = Literal["backtest", "paper", "live_micro", "live_scaled"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AIQ-BOT"
    mode: Mode = "paper"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://aiq:aiq@db:5432/aiq_db"
    redis_url: str = "redis://redis:6379/0"
    binance_api_base_url: str = "https://api.binance.com"
    cors_origins: str = "http://localhost:3066,http://127.0.0.1:3066,http://103.150.197.225:3066"
    jwt_secret: SecretStr = Field(default=SecretStr("dev-only-change-me"))
    jwt_expire_minutes: int = 15
    refresh_expire_days: int = 7
    risk_policy_path: str = "./config/risk_policy.yaml"
    prometheus_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
