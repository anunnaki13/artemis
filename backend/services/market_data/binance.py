from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.config import get_settings

Kline = list[Any]


class BinanceMarketDataClient:
    def __init__(self, base_url: str | None = None, futures_base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.binance_api_base_url).rstrip("/")
        self.futures_base_url = (futures_base_url or settings.binance_futures_api_base_url).rstrip("/")

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

    async def premium_index(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self.futures_base_url, timeout=15.0) as client:
            response = await client.get("/fapi/v1/premiumIndex")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("unexpected premium index payload")
            return [item for item in payload if isinstance(item, dict)]

    async def open_interest(self, symbol: str) -> dict[str, Any]:
        params = {"symbol": symbol.upper()}
        async with httpx.AsyncClient(base_url=self.futures_base_url, timeout=15.0) as client:
            response = await client.get("/fapi/v1/openInterest", params=params)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("unexpected open interest payload")
            return payload

    async def orderbook(self, symbol: str, limit: int = 1000) -> dict[str, Any]:
        params: dict[str, str | int] = {"symbol": symbol.upper(), "limit": limit}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.get("/api/v3/depth", params=params)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("unexpected orderbook payload")
            return payload


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


def build_combined_stream_url(base_url: str, symbols: list[str], interval: str) -> str:
    normalized_symbols = sorted({symbol.lower() for symbol in symbols if symbol.strip()})
    if not normalized_symbols:
        raise ValueError("at least one symbol is required")
    streams: list[str] = []
    for symbol in normalized_symbols:
        streams.extend(
            [
                f"{symbol}@kline_{interval}",
                f"{symbol}@miniTicker",
                f"{symbol}@bookTicker",
                f"{symbol}@depth@100ms",
            ]
        )
    return f"{base_url.rstrip('/')}/stream?streams={'/'.join(streams)}"


def parse_ws_kline_message(payload: dict[str, Any]) -> dict[str, Any]:
    kline = payload.get("k")
    if not isinstance(kline, dict):
        raise ValueError("missing kline payload")
    return {
        "symbol": str(payload["s"]).upper(),
        "timeframe": str(kline["i"]),
        "open_time": millis_to_datetime(int(kline["t"])),
        "open": Decimal(str(kline["o"])),
        "high": Decimal(str(kline["h"])),
        "low": Decimal(str(kline["l"])),
        "close": Decimal(str(kline["c"])),
        "volume": Decimal(str(kline["v"])),
        "close_time": millis_to_datetime(int(kline["T"])),
        "quote_volume": Decimal(str(kline["q"])),
        "trade_count": int(kline["n"]),
        "source": "binance_ws",
    }


def parse_ws_mini_ticker_message(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": str(payload["s"]).upper(),
        "timestamp": millis_to_datetime(int(payload["E"])),
        "last_price": Decimal(str(payload["c"])),
        "payload": payload,
    }


def parse_ws_book_ticker_message(payload: dict[str, Any]) -> dict[str, Any]:
    event_time = payload.get("E") or payload.get("T")
    if event_time is None:
        raise ValueError("missing book ticker event time")
    return {
        "symbol": str(payload["s"]).upper(),
        "timestamp": millis_to_datetime(int(event_time)),
        "bid_price": Decimal(str(payload["b"])),
        "ask_price": Decimal(str(payload["a"])),
        "payload": payload,
    }


def parse_ws_depth_message(payload: dict[str, Any]) -> dict[str, Any]:
    event_time = payload.get("E")
    bids = payload.get("b")
    asks = payload.get("a")
    best_bid = Decimal(str(bids[0][0])) if isinstance(bids, list) and bids else None
    best_ask = Decimal(str(asks[0][0])) if isinstance(asks, list) and asks else None
    if event_time is None:
        raise ValueError("missing depth event time")
    return {
        "symbol": str(payload["s"]).upper(),
        "timestamp": millis_to_datetime(int(event_time)),
        "bid_price": best_bid,
        "ask_price": best_ask,
        "payload": payload,
    }


def parse_funding_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": str(payload["symbol"]).upper(),
        "timestamp": millis_to_datetime(int(payload["time"])),
        "last_price": Decimal(str(payload["markPrice"])),
        "funding_rate": Decimal(str(payload["lastFundingRate"])),
        "payload": payload,
    }


def parse_open_interest_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": str(payload["symbol"]).upper(),
        "timestamp": millis_to_datetime(int(payload["time"])),
        "open_interest": Decimal(str(payload["openInterest"])),
        "payload": payload,
    }
