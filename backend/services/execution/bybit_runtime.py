from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.runtime_settings import get_runtime_setting


@dataclass(frozen=True)
class BybitExecutionRuntime:
    api_key: str
    api_secret: str
    base_url: str
    testnet: bool
    live_transport_enabled: bool
    account_type: str


@dataclass(frozen=True)
class BybitRuntimeValidation:
    live_ready: bool
    issues: list[str]


def parse_bool_setting(value: str | bool | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def resolve_bybit_execution_runtime(session: AsyncSession) -> BybitExecutionRuntime:
    settings = get_settings()
    api_key = await get_runtime_setting(session, "BYBIT_API_KEY")
    api_secret = await get_runtime_setting(session, "BYBIT_API_SECRET")
    if api_key is None or api_secret is None:
        raise ValueError("bybit api credentials are not configured")

    runtime_testnet = await get_runtime_setting(session, "BYBIT_TESTNET")
    runtime_base_url = await get_runtime_setting(session, "BYBIT_API_BASE_URL")
    runtime_account_type = await get_runtime_setting(session, "BYBIT_ACCOUNT_TYPE")
    live_transport_enabled = await get_runtime_setting(session, "EXECUTION_LIVE_TRANSPORT_ENABLED")

    testnet = parse_bool_setting(runtime_testnet, default=False)
    default_base_url = settings.bybit_testnet_api_base_url if testnet else settings.bybit_api_base_url

    return BybitExecutionRuntime(
        api_key=api_key,
        api_secret=api_secret,
        base_url=(runtime_base_url or default_base_url).rstrip("/"),
        testnet=testnet,
        live_transport_enabled=parse_bool_setting(
            live_transport_enabled,
            default=settings.execution_live_transport_enabled,
        ),
        account_type=(runtime_account_type or settings.bybit_account_type).upper(),
    )


async def validate_bybit_runtime(
    session: AsyncSession,
    runtime: BybitExecutionRuntime | None = None,
) -> BybitRuntimeValidation:
    effective_runtime = runtime or await resolve_bybit_execution_runtime(session)
    whitelisted_ip = await get_runtime_setting(session, "BYBIT_WHITELISTED_IP")
    withdrawal_enabled = await get_runtime_setting(session, "BYBIT_WITHDRAWAL_ENABLED")

    issues: list[str] = []
    if effective_runtime.account_type != "UNIFIED":
        issues.append("BYBIT_ACCOUNT_TYPE must be UNIFIED for Bybit live execution and private stream sync")
    if not (whitelisted_ip or "").strip():
        issues.append("BYBIT_WHITELISTED_IP must be configured before enabling Bybit private access")
    if parse_bool_setting(withdrawal_enabled, default=False):
        issues.append("BYBIT_WITHDRAWAL_ENABLED must remain false")

    return BybitRuntimeValidation(live_ready=not issues, issues=issues)


async def ensure_bybit_runtime_ready(
    session: AsyncSession,
    runtime: BybitExecutionRuntime | None = None,
) -> BybitExecutionRuntime:
    effective_runtime = runtime or await resolve_bybit_execution_runtime(session)
    validation = await validate_bybit_runtime(session, effective_runtime)
    if not validation.live_ready:
        raise ValueError("; ".join(validation.issues))
    return effective_runtime
