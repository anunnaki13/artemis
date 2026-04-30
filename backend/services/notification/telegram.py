from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


class TelegramNotifier:
    def __init__(
        self,
        config: TelegramConfig,
        base_url: str = "https://api.telegram.org",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    async def send_message(self, message: str) -> bool:
        url = f"{self.base_url}/bot{self.config.bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.chat_id,
            "text": message,
            "disable_web_page_preview": True,
        }
        async with httpx.AsyncClient(timeout=10.0, transport=self.transport) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
        return bool(body.get("ok") is True)


def mask_chat_id(chat_id: str) -> str:
    if len(chat_id) <= 4:
        return "****"
    return f"****{chat_id[-4:]}"
