import asyncio
import hashlib
import hmac
import json
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from collections.abc import Callable
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from websockets import connect

from app.config import get_settings
from app.models import ExecutionIntent
from app.schemas.execution import VenueEventState
from services.execution.account_state import SpotAccountStateService, parse_decimal
from services.execution.binance_runtime import BinanceExecutionRuntime, resolve_binance_execution_runtime
from services.execution.intent_queue import ExecutionIntentQueueService
from services.execution.worker import ExecutionWorkerService


@dataclass
class UserStreamStatus:
    running: bool = False
    subscribed: bool = False
    reconnect_attempts: int = 0
    messages_processed: int = 0
    subscription_id: int | None = None
    last_event_type: str | None = None
    last_message_at: datetime | None = None
    last_error: str | None = None


def build_user_stream_signature(api_key: str, secret: str, timestamp: int, recv_window: int) -> str:
    payload = {
        "apiKey": api_key,
        "recvWindow": recv_window,
        "timestamp": timestamp,
    }
    query = "&".join(f"{key}={payload[key]}" for key in sorted(payload))
    return hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()


def build_user_stream_subscribe_request(runtime: BinanceExecutionRuntime, recv_window: int) -> dict[str, object]:
    timestamp = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    signature = build_user_stream_signature(
        runtime.api_key,
        runtime.api_secret,
        timestamp,
        recv_window,
    )
    return {
        "id": str(uuid4()),
        "method": "userDataStream.subscribe.signature",
        "params": {
            "apiKey": runtime.api_key,
            "timestamp": timestamp,
            "recvWindow": recv_window,
            "signature": signature,
        },
    }


def resolve_user_stream_ws_url(runtime: BinanceExecutionRuntime) -> str:
    settings = get_settings()
    if runtime.testnet:
        return settings.binance_ws_api_testnet_base_url.rstrip("/")
    return settings.binance_ws_api_base_url.rstrip("/")


def compute_average_price(execution_report: dict[str, Any]) -> str | None:
    quote_filled = execution_report.get("Z")
    base_filled = execution_report.get("z")
    try:
        quote_value = Decimal(str(quote_filled))
        base_value = Decimal(str(base_filled))
    except (InvalidOperation, TypeError):
        quote_value = Decimal("0")
        base_value = Decimal("0")
    if base_value > 0:
        return format((quote_value / base_value), "f")

    last_price = execution_report.get("L")
    try:
        if Decimal(str(last_price)) > 0:
            return str(last_price)
    except (InvalidOperation, TypeError):
        return None
    return None


class BinanceUserStreamService:
    def __init__(
        self,
        session_factory: async_sessionmaker[Any] | Callable[[], Any],
        queue_service: ExecutionIntentQueueService,
        recv_window: int | None = None,
    ) -> None:
        settings = get_settings()
        self.session_factory = session_factory
        self.queue_service = queue_service
        self.recv_window = recv_window or settings.execution_user_stream_recv_window
        self._status = UserStreamStatus()
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self.account_state_service = SpotAccountStateService()

    async def start(self) -> UserStreamStatus:
        async with self._lock:
            await self._stop_locked()
            self._stop_event = asyncio.Event()
            self._status = UserStreamStatus(running=True)
            self._task = asyncio.create_task(self._run_forever())
            return self.status()

    async def stop(self) -> UserStreamStatus:
        async with self._lock:
            await self._stop_locked()
            return self.status()

    def status(self) -> UserStreamStatus:
        running = self._task is not None and not self._task.done() and not self._stop_event.is_set()
        return UserStreamStatus(
            running=running and self._status.running,
            subscribed=self._status.subscribed,
            reconnect_attempts=self._status.reconnect_attempts,
            messages_processed=self._status.messages_processed,
            subscription_id=self._status.subscription_id,
            last_event_type=self._status.last_event_type,
            last_message_at=self._status.last_message_at,
            last_error=self._status.last_error,
        )

    async def _stop_locked(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        self._status.running = False
        self._status.subscribed = False
        self._status.subscription_id = None

    async def _run_forever(self) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    async with self.session_factory() as session:
                        runtime = await resolve_binance_execution_runtime(session)
                    url = resolve_user_stream_ws_url(runtime)
                    async with connect(url, ping_interval=20, ping_timeout=20) as websocket:
                        await websocket.send(
                            json.dumps(build_user_stream_subscribe_request(runtime, self.recv_window))
                        )
                        self._status.running = True
                        self._status.subscribed = False
                        self._status.last_error = None
                        while not self._stop_event.is_set():
                            raw_message = await websocket.recv()
                            if not isinstance(raw_message, str):
                                continue
                            should_continue = await self._handle_message(raw_message)
                            if not should_continue:
                                break
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self._status.running = False
                    self._status.subscribed = False
                    self._status.subscription_id = None
                    self._status.last_error = str(exc)
                    self._status.reconnect_attempts += 1
                    await asyncio.sleep(min(self._status.reconnect_attempts, 5))
        finally:
            self._status.running = False
            self._status.subscribed = False

    async def _handle_message(self, raw_message: str) -> bool:
        payload = json.loads(raw_message)
        if not isinstance(payload, dict):
            return True

        if payload.get("status") == 200 and isinstance(payload.get("result"), dict):
            result = payload["result"]
            subscription_id = result.get("subscriptionId")
            if isinstance(subscription_id, int):
                self._status.subscribed = True
                self._status.subscription_id = subscription_id
                self._status.last_message_at = datetime.now(tz=timezone.utc)
            return True

        event = payload.get("event")
        if not isinstance(event, dict):
            return True

        event_type = str(event.get("e", ""))
        self._status.last_event_type = event_type
        self._status.last_message_at = datetime.now(tz=timezone.utc)
        self._status.messages_processed += 1

        if event_type == "executionReport":
            await self.process_execution_report(
                event,
                subscription_id=payload.get("subscriptionId"),
            )
            return True
        if event_type == "outboundAccountPosition":
            await self.process_outbound_account_position(event)
            return True
        if event_type == "balanceUpdate":
            await self.process_balance_update(event)
            return True
        if event_type == "eventStreamTerminated":
            self._status.last_error = "binance user data stream terminated"
            self._status.subscribed = False
            self._status.subscription_id = None
            return False
        return True

    async def process_execution_report(
        self,
        execution_report: dict[str, Any],
        *,
        subscription_id: object | None,
    ) -> None:
        client_order_id = execution_report.get("c")
        venue_order_id = execution_report.get("i")
        symbol = execution_report.get("s")
        venue_status = str(execution_report.get("X", execution_report.get("x", "UNKNOWN")))
        event_type = str(execution_report.get("e", "executionReport"))
        filled_notional = str(execution_report.get("Z", "0"))
        average_price = compute_average_price(execution_report)
        cumulative_quantity = parse_decimal(execution_report.get("z"))
        cumulative_quote_quantity = parse_decimal(execution_report.get("Z"))
        side = str(execution_report.get("S", "BUY"))
        execution_type = str(execution_report.get("x", ""))
        trade_id = execution_report.get("t")

        async with self.session_factory() as session:
            matched_intent = await self._persist_execution_event(
                session,
                venue="binance",
                event_type=event_type,
                venue_status=venue_status,
                symbol=str(symbol) if symbol is not None else None,
                client_order_id=str(client_order_id) if client_order_id is not None else None,
                venue_order_id=str(venue_order_id) if venue_order_id is not None else None,
                filled_notional=filled_notional,
                average_price=average_price,
                details={
                    "subscription_id": subscription_id,
                    "execution_type": execution_type,
                    "reject_reason": execution_report.get("r"),
                    "raw_event": execution_report,
                },
            )
            if (
                str(symbol or "").upper()
                and execution_type == "TRADE"
                and cumulative_quantity > Decimal("0")
                and cumulative_quote_quantity > Decimal("0")
            ):
                await self.account_state_service.apply_execution_fill(
                    session,
                    symbol=str(symbol).upper(),
                    side=side,
                    execution_intent_id=(
                        int(matched_intent.id) if matched_intent is not None and matched_intent.id is not None else None
                    ),
                    source_strategy=matched_intent.source_strategy if matched_intent is not None else None,
                    client_order_id=str(client_order_id) if client_order_id is not None else None,
                    venue_order_id=str(venue_order_id) if venue_order_id is not None else None,
                    cumulative_quantity=cumulative_quantity,
                    cumulative_quote_quantity=cumulative_quote_quantity,
                    last_trade_id=int(trade_id) if trade_id is not None else None,
                )
            await session.commit()

    async def process_outbound_account_position(self, event: dict[str, Any]) -> None:
        balances = event.get("B", [])
        if not isinstance(balances, list):
            return
        async with self.session_factory() as session:
            await self.account_state_service.apply_outbound_account_position(session, balances)
            await session.commit()

    async def process_balance_update(self, event: dict[str, Any]) -> None:
        asset = str(event.get("a", "")).upper()
        if not asset:
            return
        delta = parse_decimal(event.get("d"))
        async with self.session_factory() as session:
            await self.account_state_service.apply_balance_delta(
                session,
                asset=asset,
                delta=delta,
            )
            await session.commit()

    async def _persist_execution_event(
        self,
        session: AsyncSession,
        *,
        venue: str,
        event_type: str,
        venue_status: str,
        symbol: str | None,
        client_order_id: str | None,
        venue_order_id: str | None,
        filled_notional: str | None,
        average_price: str | None,
        details: dict[str, object],
    ) -> ExecutionIntent | None:
        intent = await self.queue_service.find_by_order_id(
            session,
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
        )
        worker = ExecutionWorkerService(self.queue_service)
        reconcile_state: VenueEventState = "unmatched"
        if intent is not None:
            intent, reconcile_state = await worker.apply_venue_event(
                session,
                intent=intent,
                venue=venue,
                event_type=event_type,
                venue_status=venue_status,
                filled_notional=filled_notional,
                average_price=average_price,
                venue_order_id=venue_order_id,
                client_order_id=client_order_id,
                details=details,
            )
        await self.queue_service.record_venue_event(
            session,
            execution_intent_id=int(intent.id) if intent is not None and intent.id is not None else None,
            venue=venue,
            event_type=event_type,
            venue_status=venue_status,
            symbol=symbol,
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
            reconcile_state=reconcile_state,
            payload={
                "filled_notional": filled_notional,
                "average_price": average_price,
                "details": details,
            },
        )
        return intent
