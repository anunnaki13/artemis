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
    primary_venue: str = "bybit"
    bybit_api_base_url: str = "https://api.bybit.com"
    bybit_testnet_api_base_url: str = "https://api-testnet.bybit.com"
    bybit_ws_public_spot_base_url: str = "wss://stream.bybit.com/v5/public/spot"
    bybit_ws_public_linear_base_url: str = "wss://stream.bybit.com/v5/public/linear"
    bybit_ws_private_base_url: str = "wss://stream.bybit.com/v5/private"
    bybit_ws_private_testnet_base_url: str = "wss://stream-testnet.bybit.com/v5/private"
    bybit_ws_public_spot_testnet_base_url: str = "wss://stream-testnet.bybit.com/v5/public/spot"
    bybit_account_type: str = "UNIFIED"
    market_data_poll_interval_seconds: int = 30
    orderbook_persist_interval_seconds: int = 5
    orderbook_snapshot_depth_levels: int = 20
    execution_dispatch_timeout_seconds: int = 30
    execution_live_transport_enabled: bool = False
    execution_user_stream_recv_window: int = 5000
    cors_origins: str = "http://localhost:3066,http://127.0.0.1:3066,http://103.150.197.225:3066"
    jwt_secret: SecretStr = Field(default=SecretStr("dev-only-change-me"))
    jwt_expire_minutes: int = 15
    auth_cookie_secure: bool = False
    auth_cookie_name: str = "aiq_access_token"
    refresh_expire_days: int = 7
    risk_policy_path: str = "./config/risk_policy.yaml"
    capital_profiles_path: str = "./config/capital_profiles.yaml"
    growth_plan_path: str = "./config/growth_plan.yaml"
    universe_config_path: str = "./config/edge/universe.yaml"
    universe_blacklist_path: str = "./config/edge/blacklist.yaml"
    reports_output_dir: str = "./var/reports"
    reports_daily_digest_enabled: bool = True
    reports_daily_digest_hour_utc: int = 0
    reports_daily_digest_retention_days: int = 30
    reports_daily_digest_telegram_enabled: bool = True
    prometheus_enabled: bool = True
    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
