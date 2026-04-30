from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret
from app.models import AppSetting


async def get_runtime_setting(session: AsyncSession, key: str, fallback: str | None = None) -> str | None:
    row = await session.get(AppSetting, key)
    if row is None or row.encrypted_value is None:
        return fallback
    return decrypt_secret(row.encrypted_value)
