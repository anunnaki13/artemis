from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.config import get_settings

Kline = list[Any]


class BybitMarketDataClient:
    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.bybit_api_base_url).rstrip("/")

    async def instruments_info(self, category: str = "spot", limit: int = 1000) -> dict[str, Any]:
        params: dict[str, str | int] = {"category": category, "limit": limit}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.get("/v5/market/instruments-info", params=params)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("unexpected instruments payload")
            return payload

    async def klines(self, symbol: str, interval: str, limit: int, category: str = "spot") -> list[Kline]:
        params: dict[str, str | int] = {
            "category": category,
            "symbol": symbol.upper(),
            "interval": normalize_interval(interval),
            "limit": limit,
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.get("/v5/market/kline", params=params)
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("result", {}).get("list", []) if isinstance(payload, dict) else []
            if not isinstance(rows, list):
                raise ValueError("unexpected kline payload")
            normalized_rows = [row for row in rows if isinstance(row, list)]
            normalized_rows.reverse()
            return normalized_rows

    async def ticker_24h(self, category: str = "spot") -> list[dict[str, Any]]:
        params: dict[str, str] = {"category": category}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.get("/v5/market/tickers", params=params)
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("result", {}).get("list", []) if isinstance(payload, dict) else []
            if not isinstance(rows, list):
                raise ValueError("unexpected ticker payload")
            return [normalize_ticker_row(item) for item in rows if isinstance(item, dict)]

    async def funding_ticker(self, symbol: str) -> dict[str, Any]:
        params: dict[str, str] = {"category": "linear", "symbol": symbol.upper()}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.get("/v5/market/tickers", params=params)
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("result", {}).get("list", []) if isinstance(payload, dict) else []
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
                raise ValueError("unexpected funding ticker payload")
            return rows[0]

    async def open_interest(self, symbol: str, interval_time: str = "5min") -> dict[str, Any]:
        params: dict[str, str] = {
            "category": "linear",
            "symbol": symbol.upper(),
            "intervalTime": interval_time,
            "limit": "1",
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.get("/v5/market/open-interest", params=params)
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("result", {}).get("list", []) if isinstance(payload, dict) else []
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
                raise ValueError("unexpected open interest payload")
            return rows[0]

    async def orderbook(self, symbol: str, category: str = "spot", limit: int = 200) -> dict[str, Any]:
        params: dict[str, str | int] = {"category": category, "symbol": symbol.upper(), "limit": limit}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.get("/v5/market/orderbook", params=params)
            response.raise_for_status()
            payload = response.json()
            orderbook = payload.get("result") if isinstance(payload, dict) else None
            if not isinstance(orderbook, dict):
                raise ValueError("unexpected orderbook payload")
            return orderbook


def normalize_interval(interval: str) -> str:
    mapping = {"1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30", "1h": "60", "4h": "240", "1d": "D"}
    return mapping.get(interval, interval)


def decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    decimal = Decimal(value)
    if decimal == 0:
        return None
    return decimal


def normalize_ticker_row(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "quoteVolume": payload.get("turnover24h", "0"),
        "priceChangePercent": payload.get("price24hPcnt", "0"),
    }


def extract_symbol_filters(symbol_payload: dict[str, Any]) -> dict[str, Decimal | None]:
    lot_size_filter = symbol_payload.get("lotSizeFilter", {}) if isinstance(symbol_payload.get("lotSizeFilter"), dict) else {}
    price_filter = symbol_payload.get("priceFilter", {}) if isinstance(symbol_payload.get("priceFilter"), dict) else {}
    qty_step = lot_size_filter.get("qtyStep") or lot_size_filter.get("basePrecision") or lot_size_filter.get("minOrderQty")
    return {
        "tick_size": decimal_or_none(str(price_filter.get("tickSize")) if price_filter else None),
        "step_size": decimal_or_none(str(qty_step) if qty_step else None),
        "min_notional": decimal_or_none(
            str(lot_size_filter.get("minOrderAmt") or lot_size_filter.get("minNotionalValue"))
            if lot_size_filter
            else None
        ),
    }


def millis_to_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def parse_kline(symbol: str, interval: str, kline: Kline) -> dict[str, Any]:
    open_time = int(kline[0])
    return {
        "symbol": symbol.upper(),
        "timeframe": interval,
        "open_time": millis_to_datetime(open_time),
        "open": Decimal(str(kline[1])),
        "high": Decimal(str(kline[2])),
        "low": Decimal(str(kline[3])),
        "close": Decimal(str(kline[4])),
        "volume": Decimal(str(kline[5])),
        "close_time": millis_to_datetime(open_time + interval_to_millis(interval) - 1),
        "quote_volume": Decimal(str(kline[6])),
        "trade_count": 0,
        "source": "bybit",
    }


def interval_to_millis(interval: str) -> int:
    mapping = {
        "1m": 60_000,
        "3m": 180_000,
        "5m": 300_000,
        "15m": 900_000,
        "30m": 1_800_000,
        "1h": 3_600_000,
        "4h": 14_400_000,
        "1d": 86_400_000,
    }
    return mapping.get(interval, 60_000)


def topic_for_symbol(symbol: str, interval: str) -> list[str]:
    normalized = symbol.upper()
    return [
        f"kline.{normalize_interval(interval)}.{normalized}",
        f"tickers.{normalized}",
        f"orderbook.50.{normalized}",
    ]


def parse_ws_kline_message(topic: str, payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("data")
    row = rows[0] if isinstance(rows, list) and rows else rows
    if not isinstance(row, dict):
        raise ValueError("missing bybit kline payload")
    interval = str(topic.split(".")[1])
    normalized_interval = {
        "1": "1m",
        "3": "3m",
        "5": "5m",
        "15": "15m",
        "30": "30m",
        "60": "1h",
        "240": "4h",
        "D": "1d",
    }.get(interval, interval)
    open_time = int(row["start"])
    return {
        "symbol": str(row["symbol"]).upper(),
        "timeframe": normalized_interval,
        "open_time": millis_to_datetime(open_time),
        "open": Decimal(str(row["open"])),
        "high": Decimal(str(row["high"])),
        "low": Decimal(str(row["low"])),
        "close": Decimal(str(row["close"])),
        "volume": Decimal(str(row["volume"])),
        "close_time": millis_to_datetime(int(row["end"])),
        "quote_volume": Decimal(str(row.get("turnover", "0"))),
        "trade_count": 0,
        "source": "bybit_ws",
    }


def parse_ws_ticker_message(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("data")
    row = rows[0] if isinstance(rows, list) and rows else rows
    if not isinstance(row, dict):
        raise ValueError("missing bybit ticker payload")
    event_time = payload.get("ts")
    if event_time is None:
        raise ValueError("missing bybit ticker timestamp")
    return {
        "symbol": str(row["symbol"]).upper(),
        "timestamp": millis_to_datetime(int(str(event_time))),
        "last_price": Decimal(str(row.get("lastPrice", "0"))),
        "bid_price": decimal_or_none(str(row.get("bid1Price"))) if row.get("bid1Price") is not None else None,
        "ask_price": decimal_or_none(str(row.get("ask1Price"))) if row.get("ask1Price") is not None else None,
        "payload": row,
    }


def parse_ws_depth_message(symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("missing bybit depth payload")
    bids = data.get("b", [])
    asks = data.get("a", [])
    event_time = payload.get("ts") or data.get("ts")
    if event_time is None:
        raise ValueError("missing bybit depth timestamp")
    best_bid = Decimal(str(bids[0][0])) if isinstance(bids, list) and bids else None
    best_ask = Decimal(str(asks[0][0])) if isinstance(asks, list) and asks else None
    return {
        "symbol": symbol.upper(),
        "timestamp": millis_to_datetime(int(event_time)),
        "bid_price": best_bid,
        "ask_price": best_ask,
        "payload": payload,
    }


def parse_funding_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    timestamp = payload.get("nextFundingTime") or payload.get("time")
    return {
        "symbol": str(payload["symbol"]).upper(),
        "timestamp": millis_to_datetime(int(str(timestamp))),
        "last_price": Decimal(str(payload["markPrice"])),
        "funding_rate": Decimal(str(payload["fundingRate"])),
        "payload": payload,
    }


def parse_open_interest_snapshot(symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
    timestamp = payload.get("timestamp") or payload.get("ts")
    return {
        "symbol": symbol.upper(),
        "timestamp": millis_to_datetime(int(str(timestamp))),
        "open_interest": Decimal(str(payload["openInterest"])),
        "payload": payload,
    }
