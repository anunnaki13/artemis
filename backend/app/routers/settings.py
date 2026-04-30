from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from app.db import get_session
from app.models import AppSetting
from app.schemas.settings import SettingRead, SettingsReadResponse, SettingsUpdateRequest

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED_SETTINGS = {
    "OWNER_EMAIL",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "BINANCE_TESTNET",
    "BINANCE_VIP_TIER",
    "BINANCE_WHITELISTED_IP",
    "OPENROUTER_API_KEY",
    "AI_PRIMARY_MODEL",
    "AI_FAST_MODEL",
    "AI_HEAVY_MODEL",
    "AI_MAX_COST_USD_PER_DAY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "SMTP_HOST",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "EMAIL_FROM",
    "EMAIL_TO",
    "HEALTHCHECK_PING_URL",
    "DEAD_MAN_SWITCH_WEBHOOK",
    "PROMETHEUS_ENABLED",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "REDIS_PASSWORD",
    "REDIS_URL",
    "JWT_SECRET",
}

NON_SECRET_SETTINGS = {
    "OWNER_EMAIL",
    "BINANCE_TESTNET",
    "BINANCE_VIP_TIER",
    "BINANCE_WHITELISTED_IP",
    "AI_PRIMARY_MODEL",
    "AI_FAST_MODEL",
    "AI_HEAVY_MODEL",
    "AI_MAX_COST_USD_PER_DAY",
    "TELEGRAM_CHAT_ID",
    "SMTP_HOST",
    "SMTP_USER",
    "EMAIL_FROM",
    "EMAIL_TO",
    "PROMETHEUS_ENABLED",
}


@router.get("", response_model=SettingsReadResponse)
async def read_settings(session: AsyncSession = Depends(get_session)) -> SettingsReadResponse:
    rows = (await session.scalars(select(AppSetting))).all()
    by_key = {row.key: row for row in rows}
    settings: list[SettingRead] = []
    for key in sorted(ALLOWED_SETTINGS):
        row = by_key.get(key)
        if row is None or row.encrypted_value is None:
            settings.append(
                SettingRead(
                    key=key,
                    value=None,
                    is_secret=key not in NON_SECRET_SETTINGS,
                    configured=False,
                )
            )
            continue
        value = decrypt_secret(row.encrypted_value)
        is_secret = row.is_secret
        settings.append(
            SettingRead(
                key=key,
                value=mask_secret(value) if is_secret else value,
                is_secret=is_secret,
                configured=True,
            )
        )
    return SettingsReadResponse(settings=settings)


@router.put("", response_model=SettingsReadResponse)
async def update_settings(
    payload: SettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> SettingsReadResponse:
    for item in payload.settings:
        if item.key not in ALLOWED_SETTINGS:
            continue
        if item.value is None or item.value == "":
            continue
        row = await session.get(AppSetting, item.key)
        is_secret = item.key not in NON_SECRET_SETTINGS
        encrypted_value = encrypt_secret(item.value)
        if row is None:
            row = AppSetting(key=item.key, encrypted_value=encrypted_value, is_secret=is_secret)
            session.add(row)
        else:
            row.encrypted_value = encrypted_value
            row.is_secret = is_secret
    await session.commit()
    return await read_settings(session)
