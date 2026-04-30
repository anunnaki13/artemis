import httpx
from services.notification.telegram import TelegramConfig, TelegramNotifier, mask_chat_id


async def test_telegram_notifier_sends_message() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = request.read().decode()
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)

    notifier = TelegramNotifier(
        TelegramConfig(bot_token="123456:secret", chat_id="987654321"),
        base_url="https://telegram.test",
        transport=transport,
    )

    assert await notifier.send_message("hello") is True
    assert captured["url"] == "https://telegram.test/bot123456:secret/sendMessage"
    assert '"chat_id":"987654321"' in str(captured["json"])
    assert '"text":"hello"' in str(captured["json"])


def test_mask_chat_id() -> None:
    assert mask_chat_id("987654321") == "****4321"
    assert mask_chat_id("123") == "****"
