from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.runtime_settings import get_runtime_setting
from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas.notifications import TelegramTestRequest, TelegramTestResponse
from services.notification.telegram import TelegramConfig, TelegramNotifier, mask_chat_id

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/telegram/test", response_model=TelegramTestResponse)
async def test_telegram(
    payload: TelegramTestRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TelegramTestResponse:
    settings = get_settings()
    fallback_token = (
        settings.telegram_bot_token.get_secret_value()
        if settings.telegram_bot_token is not None
        else None
    )
    bot_token = await get_runtime_setting(session, "TELEGRAM_BOT_TOKEN", fallback_token)
    chat_id = await get_runtime_setting(session, "TELEGRAM_CHAT_ID", settings.telegram_chat_id)
    if bot_token is None or chat_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="telegram credentials are not configured",
        )

    notifier = TelegramNotifier(TelegramConfig(bot_token=bot_token, chat_id=chat_id))
    delivered = await notifier.send_message(payload.message)
    return TelegramTestResponse(delivered=delivered, destination=mask_chat_id(chat_id))
