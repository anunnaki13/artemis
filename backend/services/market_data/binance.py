from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.config import get_settings

Kline = list[Any]


class BinanceMarketDataClient:
    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.binance_api_base_url).rstrip("/")

    async def exchange_info(self) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.get("/api/v3/exchangeInfo")
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

    async def klines(self, symbol: str, interval: str, limit: int) -> list[Kline]:
        params: dict[str, str | int] = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.get("/api/v3/klines", params=params)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("unexpected klines payload")
            return payload

    async def ticker_24h(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.get("/api/v3/ticker/24hr")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("unexpected ticker payload")
            return [item for item in payload if isinstance(item, dict)]


def decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    decimal = Decimal(value)
    if decimal == 0:
        return None
    return decimal


def extract_symbol_filters(symbol_payload: dict[str, Any]) -> dict[str, Decimal | None]:
    filters = {
        str(item.get("filterType")): item
        for item in symbol_payload.get("filters", [])
        if isinstance(item, dict)
    }
    price_filter = filters.get("PRICE_FILTER", {})
    lot_size = filters.get("LOT_SIZE", {})
    min_notional_filter = filters.get("MIN_NOTIONAL", {}) or filters.get("NOTIONAL", {})
    return {
        "tick_size": decimal_or_none(str(price_filter.get("tickSize")) if price_filter else None),
        "step_size": decimal_or_none(str(lot_size.get("stepSize")) if lot_size else None),
        "min_notional": decimal_or_none(
            str(min_notional_filter.get("minNotional")) if min_notional_filter else None
        ),
    }


def millis_to_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def parse_kline(symbol: str, interval: str, kline: Kline) -> dict[str, Any]:
    return {
        "symbol": symbol.upper(),
        "timeframe": interval,
        "open_time": millis_to_datetime(int(kline[0])),
        "open": Decimal(str(kline[1])),
        "high": Decimal(str(kline[2])),
        "low": Decimal(str(kline[3])),
        "close": Decimal(str(kline[4])),
        "volume": Decimal(str(kline[5])),
        "close_time": millis_to_datetime(int(kline[6])),
        "quote_volume": Decimal(str(kline[7])),
        "trade_count": int(kline[8]),
        "source": "binance",
    }
