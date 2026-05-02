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
from services.market_data.bybit import (
    BybitMarketDataClient,
    millis_to_datetime,
    parse_funding_snapshot,
    parse_open_interest_snapshot,
    parse_ws_depth_message,
    parse_ws_kline_message,
    parse_ws_ticker_message,
    topic_for_symbol,
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


class BybitMarketStreamService:
    def __init__(
        self,
        session_factory: async_sessionmaker[Any],
        ws_public_spot_base_url: str | None = None,
        poll_interval_seconds: int | None = None,
    ) -> None:
        settings = get_settings()
        self.session_factory = session_factory
        self.ws_public_spot_base_url = (
            ws_public_spot_base_url or settings.bybit_ws_public_spot_base_url
        ).rstrip("/")
        self.client = BybitMarketDataClient()
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
        topics: list[str] = []
        for symbol in symbols:
            topics.extend(topic_for_symbol(symbol, interval))
        subscribe_payload = {"op": "subscribe", "args": topics}
        while not self._stop_event.is_set():
            try:
                async with connect(self.ws_public_spot_base_url, ping_interval=20, ping_timeout=20) as websocket:
                    await websocket.send(json.dumps(subscribe_payload))
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
        while not self._stop_event.is_set():
            try:
                async with self.session_factory() as session:
                    for symbol in symbols:
                        funding_payload = await self.client.funding_ticker(symbol)
                        merged_values = parse_funding_snapshot(funding_payload)
                        try:
                            open_interest_payload = await self.client.open_interest(symbol)
                            merged_values["open_interest"] = parse_open_interest_snapshot(
                                symbol, open_interest_payload
                            )["open_interest"]
                            merged_values["payload"] = {
                                "funding_ticker": funding_payload,
                                "open_interest": open_interest_payload,
                            }
                        except Exception:
                            merged_values["payload"] = {"funding_ticker": funding_payload}
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
        topic = str(payload.get("topic", ""))
        if topic.startswith("kline."):
            candle_values = parse_ws_kline_message(topic, payload)
            async with self.session_factory() as session:
                statement = insert(Candle).values(**candle_values)
                await session.execute(
                    statement.on_conflict_do_update(
                        constraint="uq_candles_symbol_timeframe_open_time",
                        set_=candle_values,
                    )
                )
                await session.commit()
        elif topic.startswith("tickers."):
            snapshot_values = parse_ws_ticker_message(payload)
            async with self.session_factory() as session:
                await session.execute(insert(MarketSnapshot).values(**snapshot_values))
                await session.commit()
        elif topic.startswith("orderbook."):
            symbol = topic.split(".")[-1].upper()
            await self._apply_depth_update(symbol, payload)
            async with self.session_factory() as session:
                depth_snapshot = parse_ws_depth_message(symbol, payload)
                orderbook = self._orderbooks.get(symbol)
                if orderbook is not None:
                    metrics = orderbook.metrics()
                    depth_snapshot["payload"] = {
                        "depth_update": payload,
                        "metrics": metrics_to_payload(metrics),
                    }
                await session.execute(insert(MarketSnapshot).values(**depth_snapshot))
                if orderbook is not None:
                    orderbook_snapshot = self._build_orderbook_snapshot(orderbook)
                    if orderbook_snapshot is not None:
                        await session.execute(insert(OrderBookSnapshot).values(**orderbook_snapshot))
                await session.commit()
        self._status.messages_processed += 1
        self._status.last_message_at = datetime.now(tz=timezone.utc)

    async def _bootstrap_orderbooks(self, symbols: list[str]) -> None:
        for symbol in symbols:
            snapshot = await self.client.orderbook(symbol)
            bids = snapshot.get("b", [])
            asks = snapshot.get("a", [])
            last_update_id = int(snapshot.get("u", 0))
            orderbook = OrderBookState(symbol=symbol)
            orderbook.load_snapshot(
                bids=bids,
                asks=asks,
                last_update_id=last_update_id,
                updated_at=millis_to_datetime(int(snapshot.get("ts", int(datetime.now(tz=timezone.utc).timestamp() * 1000)))),
            )
            self._orderbooks[symbol] = orderbook

    async def _apply_depth_update(self, symbol: str, payload: dict[str, Any]) -> None:
        data = payload.get("data")
        if not isinstance(data, dict):
            return
        orderbook = self._orderbooks.get(symbol)
        if orderbook is None:
            await self._bootstrap_orderbooks([symbol])
            orderbook = self._orderbooks.get(symbol)
            if orderbook is None:
                return
        update_id = int(data.get("u", 0))
        bids = data.get("b", [])
        asks = data.get("a", [])
        orderbook.apply_depth_update(
            bids=bids if isinstance(bids, list) else [],
            asks=asks if isinstance(asks, list) else [],
            first_update_id=update_id,
            final_update_id=update_id,
            updated_at=millis_to_datetime(int(payload.get("ts", int(datetime.now(tz=timezone.utc).timestamp() * 1000)))),
        )

    def _build_orderbook_snapshot(self, orderbook: OrderBookState) -> dict[str, Any] | None:
        now = datetime.now(tz=timezone.utc)
        last_persisted_at = self._last_persisted_at.get(orderbook.symbol)
        if (
            last_persisted_at is not None
            and (now - last_persisted_at).total_seconds() < self.orderbook_persist_interval_seconds
        ):
            return None
        metrics = orderbook.metrics()
        bids = orderbook.top_bids(self.orderbook_snapshot_depth_levels)
        asks = orderbook.top_asks(self.orderbook_snapshot_depth_levels)
        self._last_persisted_at[orderbook.symbol] = now
        return {
            "symbol": orderbook.symbol,
            "timestamp": metrics.updated_at or now,
            "bids": levels_to_payload(bids),
            "asks": levels_to_payload(asks),
            "metrics": metrics_to_payload(metrics),
        }
