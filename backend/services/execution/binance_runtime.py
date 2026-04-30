from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.runtime_settings import get_runtime_setting


@dataclass(frozen=True)
class BinanceExecutionRuntime:
    api_key: str
    api_secret: str
    base_url: str
    testnet: bool
    live_transport_enabled: bool


def parse_bool_setting(value: str | bool | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def resolve_binance_execution_runtime(session: AsyncSession) -> BinanceExecutionRuntime:
    settings = get_settings()
    api_key = await get_runtime_setting(session, "BINANCE_API_KEY")
    api_secret = await get_runtime_setting(session, "BINANCE_API_SECRET")
    if api_key is None or api_secret is None:
        raise ValueError("binance api credentials are not configured")

    runtime_testnet = await get_runtime_setting(session, "BINANCE_TESTNET")
    runtime_base_url = await get_runtime_setting(session, "BINANCE_SPOT_API_BASE_URL")
    live_transport_enabled = await get_runtime_setting(session, "EXECUTION_LIVE_TRANSPORT_ENABLED")

    testnet = parse_bool_setting(runtime_testnet, default=False)
    default_base_url = (
        settings.binance_spot_testnet_api_base_url if testnet else settings.binance_api_base_url
    )

    return BinanceExecutionRuntime(
        api_key=api_key,
        api_secret=api_secret,
        base_url=(runtime_base_url or default_base_url).rstrip("/"),
        testnet=testnet,
        live_transport_enabled=parse_bool_setting(
            live_transport_enabled,
            default=settings.execution_live_transport_enabled,
        ),
    )
