from pydantic import BaseModel, Field


class TelegramTestRequest(BaseModel):
    message: str = Field(default="AIQ-BOT Telegram notification test", min_length=1, max_length=512)


class TelegramTestResponse(BaseModel):
    delivered: bool
    destination: str
