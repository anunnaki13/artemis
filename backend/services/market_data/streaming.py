import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker
from websockets import connect

from app.config import get_settings
from app.models import Candle, MarketSnapshot, OrderBookSnapshot
from services.market_data.binance import (
    BinanceMarketDataClient,
    build_combined_stream_url,
    millis_to_datetime,
    parse_funding_snapshot,
    parse_ws_book_ticker_message,
    parse_ws_depth_message,
    parse_ws_kline_message,
    parse_ws_mini_ticker_message,
    parse_open_interest_snapshot,
)
from services.market_data.orderbook import OrderBookState
from services.market_data.orderbook import levels_to_payload, metrics_to_payload


@dataclass
class StreamStatus:
    running: bool = False
    symbols: list[str] = field(default_factory=list)
    interval: str | None = None
    reconnect_attempts: int = 0
    messages_processed: int = 0
    poll_cycles: int = 0
    last_message_at: datetime | None = None
    last_error: str | None = None


class BinanceMarketStreamService:
    def __init__(
        self,
        session_factory: async_sessionmaker[Any],
        ws_base_url: str | None = None,
        futures_api_base_url: str | None = None,
        poll_interval_seconds: int | None = None,
    ) -> None:
        settings = get_settings()
        self.session_factory = session_factory
        self.ws_base_url = (ws_base_url or settings.binance_ws_base_url).rstrip("/")
        self.client = BinanceMarketDataClient(futures_base_url=futures_api_base_url)
        self.poll_interval_seconds = poll_interval_seconds or settings.market_data_poll_interval_seconds
        self._status = StreamStatus()
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._orderbooks: dict[str, OrderBookState] = {}
        self._last_persisted_at: dict[str, datetime] = {}
        self.orderbook_persist_interval_seconds = settings.orderbook_persist_interval_seconds
        self.orderbook_snapshot_depth_levels = settings.orderbook_snapshot_depth_levels

    async def start(self, symbols: list[str], interval: str) -> StreamStatus:
        normalized_symbols = sorted({symbol.upper() for symbol in symbols if symbol.strip()})
        if not normalized_symbols:
            raise ValueError("at least one symbol is required")

        async with self._lock:
            await self._stop_locked()
            self._stop_event = asyncio.Event()
            self._status = StreamStatus(running=True, symbols=normalized_symbols, interval=interval)
            self._task = asyncio.create_task(self._run_forever(normalized_symbols, interval))
            return self.status()

    async def stop(self) -> StreamStatus:
        async with self._lock:
            await self._stop_locked()
            return self.status()

    def status(self) -> StreamStatus:
        running = self._task is not None and not self._task.done() and not self._stop_event.is_set()
        return StreamStatus(
            running=running and self._status.running,
            symbols=list(self._status.symbols),
            interval=self._status.interval,
            reconnect_attempts=self._status.reconnect_attempts,
            messages_processed=self._status.messages_processed,
            poll_cycles=self._status.poll_cycles,
            last_message_at=self._status.last_message_at,
            last_error=self._status.last_error,
        )

    def orderbook(self, symbol: str) -> OrderBookState | None:
        return self._orderbooks.get(symbol.upper())

    async def _stop_locked(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        self._status.running = False
        self._last_persisted_at.clear()

    async def _run_forever(self, symbols: list[str], interval: str) -> None:
        try:
            await self._bootstrap_orderbooks(symbols)
            await asyncio.gather(
                self._run_ws_forever(symbols, interval),
                self._run_funding_poll_forever(symbols),
            )
        finally:
            self._status.running = False

    async def _run_ws_forever(self, symbols: list[str], interval: str) -> None:
        url = build_combined_stream_url(self.ws_base_url, symbols, interval)
        while not self._stop_event.is_set():
            try:
                async with connect(url, ping_interval=20, ping_timeout=20) as websocket:
                    self._status.running = True
                    self._status.last_error = None
                    while not self._stop_event.is_set():
                        raw_message = await websocket.recv()
                        if not isinstance(raw_message, str):
                            continue
                        await self._handle_message(raw_message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._status.running = False
                self._status.last_error = str(exc)
                self._status.reconnect_attempts += 1
                await asyncio.sleep(min(self._status.reconnect_attempts, 5))

    async def _run_funding_poll_forever(self, symbols: list[str]) -> None:
        target_symbols = set(symbols)
        while not self._stop_event.is_set():
            try:
                premium_index_payloads = await self.client.premium_index()
                premium_by_symbol = {
                    str(item.get("symbol", "")).upper(): item
                    for item in premium_index_payloads
                    if str(item.get("symbol", "")).upper() in target_symbols
                }

                async with self.session_factory() as session:
                    for symbol in symbols:
                        premium_payload = premium_by_symbol.get(symbol)
                        if premium_payload is None:
                            continue
                        merged_values = parse_funding_snapshot(premium_payload)
                        try:
                            open_interest_payload = await self.client.open_interest(symbol)
                            merged_values["open_interest"] = parse_open_interest_snapshot(
                                open_interest_payload
                            )["open_interest"]
                            merged_values["payload"] = {
                                "premium_index": premium_payload,
                                "open_interest": open_interest_payload,
                            }
                        except Exception:
                            merged_values["payload"] = {"premium_index": premium_payload}
                        await session.execute(insert(MarketSnapshot).values(**merged_values))
                    await session.commit()

                self._status.poll_cycles += 1
                self._status.last_message_at = datetime.now(tz=timezone.utc)
                self._status.last_error = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._status.last_error = str(exc)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except TimeoutError:
                continue

    async def _handle_message(self, raw_message: str) -> None:
        payload = json.loads(raw_message)
        if not isinstance(payload, dict):
            return
        data = payload.get("data", payload)
        if not isinstance(data, dict):
            return

        stream_name = str(payload.get("stream", "")).lower()
        event_type = str(data.get("e", "")).lower()
        if event_type == "depthupdate" or "@depth@" in stream_name:
            await self._apply_depth_update(data)
        snapshot_values = self._snapshot_values(stream_name, event_type, data)
        candle_values = parse_ws_kline_message(data) if event_type == "kline" else None

        async with self.session_factory() as session:
            if candle_values is not None:
                statement = insert(Candle).values(**candle_values)
                await session.execute(
                    statement.on_conflict_do_update(
                        constraint="uq_candles_symbol_timeframe_open_time",
                        set_=candle_values,
                    )
                )
            if snapshot_values is not None:
                await session.execute(insert(MarketSnapshot).values(**snapshot_values))
            if event_type == "depthupdate" or "@depth@" in stream_name:
                orderbook = self._orderbooks.get(str(data["s"]).upper())
                if orderbook is not None:
                    orderbook_snapshot = self._build_orderbook_snapshot(orderbook)
                    if orderbook_snapshot is not None:
                        await session.execute(insert(OrderBookSnapshot).values(**orderbook_snapshot))
            await session.commit()

        self._status.messages_processed += 1
        self._status.last_message_at = datetime.now(tz=timezone.utc)

    def _snapshot_values(
        self,
        stream_name: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        if event_type == "24hrminiticker" or stream_name.endswith("@miniticker"):
            return parse_ws_mini_ticker_message(payload)
        if event_type == "bookticker" or stream_name.endswith("@bookticker"):
            book_payload = dict(payload)
            if "E" not in book_payload and "T" not in book_payload:
                book_payload["E"] = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
            return parse_ws_book_ticker_message(book_payload)
        if event_type == "depthupdate" or "@depth@" in stream_name:
            depth_snapshot = parse_ws_depth_message(payload)
            symbol = str(payload["s"]).upper()
            orderbook = self._orderbooks.get(symbol)
            if orderbook is not None:
                metrics = orderbook.metrics()
                depth_snapshot["payload"] = {
                    "depth_update": payload,
                    "metrics": metrics_to_payload(metrics),
                }
            return depth_snapshot
        return None

    async def _bootstrap_orderbooks(self, symbols: list[str]) -> None:
        for symbol in symbols:
            await self._bootstrap_orderbook_symbol(symbol)

    async def _bootstrap_orderbook_symbol(self, symbol: str) -> None:
        snapshot = await self.client.orderbook(symbol)
        bids = snapshot.get("bids", [])
        asks = snapshot.get("asks", [])
        last_update_id = snapshot.get("lastUpdateId")
        if not isinstance(bids, list) or not isinstance(asks, list) or not isinstance(last_update_id, int):
            raise ValueError(f"unexpected orderbook snapshot payload for {symbol}")
        orderbook = OrderBookState(symbol=symbol)
        orderbook.load_snapshot(
            bids=bids,
            asks=asks,
            last_update_id=last_update_id,
            updated_at=datetime.now(tz=timezone.utc),
        )
        self._orderbooks[symbol] = orderbook
        self._last_persisted_at.pop(symbol, None)

    async def _apply_depth_update(self, payload: dict[str, Any]) -> None:
        symbol = str(payload["s"]).upper()
        orderbook = self._orderbooks.get(symbol)
        if orderbook is None:
            return
        first_update_id = int(payload["U"])
        final_update_id = int(payload["u"])
        bids = payload.get("b", [])
        asks = payload.get("a", [])
        if not isinstance(bids, list) or not isinstance(asks, list):
            raise ValueError("unexpected depth update payload")
        try:
            orderbook.apply_depth_update(
                first_update_id=first_update_id,
                final_update_id=final_update_id,
                bids=bids,
                asks=asks,
                updated_at=millis_to_datetime(int(payload["E"])),
            )
        except ValueError:
            await self._bootstrap_orderbook_symbol(symbol)

    def _build_orderbook_snapshot(self, orderbook: OrderBookState) -> dict[str, Any] | None:
        if orderbook.updated_at is None:
            return None
        last_persisted_at = self._last_persisted_at.get(orderbook.symbol)
        interval_seconds = max(self.orderbook_persist_interval_seconds, 1)
        if last_persisted_at is not None:
            elapsed = (orderbook.updated_at - last_persisted_at).total_seconds()
            if elapsed < interval_seconds:
                return None
        top_bids = orderbook.top_bids(self.orderbook_snapshot_depth_levels)
        top_asks = orderbook.top_asks(self.orderbook_snapshot_depth_levels)
        metrics = orderbook.metrics()
        self._last_persisted_at[orderbook.symbol] = orderbook.updated_at
        return {
            "symbol": orderbook.symbol,
            "timestamp": orderbook.updated_at,
            "last_update_id": orderbook.last_update_id,
            "bids": levels_to_payload(top_bids),
            "asks": levels_to_payload(top_asks),
            "metrics": metrics_to_payload(metrics),
        }
