import asyncio
import hashlib
import hmac
import json
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from websockets import connect

from app.config import get_settings
from app.models import ExecutionIntent
from app.schemas.execution import VenueEventState
from services.execution.account_state import SpotAccountStateService, parse_decimal
from services.execution.bybit_runtime import BybitExecutionRuntime, resolve_bybit_execution_runtime
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


def build_ws_signature(secret: str, expires: int) -> str:
    payload = f"GET/realtime{expires}"
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def resolve_user_stream_ws_url(runtime: BybitExecutionRuntime) -> str:
    settings = get_settings()
    if runtime.testnet:
        return settings.bybit_ws_private_testnet_base_url.rstrip("/")
    return settings.bybit_ws_private_base_url.rstrip("/")


class BybitUserStreamService:
    def __init__(
        self,
        session_factory: async_sessionmaker[Any] | Callable[[], Any],
        queue_service: ExecutionIntentQueueService,
    ) -> None:
        self.session_factory = session_factory
        self.queue_service = queue_service
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
                        runtime = await resolve_bybit_execution_runtime(session)
                    url = resolve_user_stream_ws_url(runtime)
                    expires = int(datetime.now(tz=timezone.utc).timestamp() * 1000) + 10_000
                    auth_payload = {
                        "op": "auth",
                        "args": [
                            runtime.api_key,
                            expires,
                            build_ws_signature(runtime.api_secret, expires),
                        ],
                    }
                    subscribe_payload = {"op": "subscribe", "args": ["order", "wallet", "execution"]}
                    async with connect(url, ping_interval=20, ping_timeout=20) as websocket:
                        await websocket.send(json.dumps(auth_payload))
                        await websocket.send(json.dumps(subscribe_payload))
                        self._status.running = True
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
        if payload.get("op") == "auth":
            if payload.get("success") is True:
                self._status.subscribed = True
                self._status.last_message_at = datetime.now(tz=timezone.utc)
                return True
            self._status.last_error = str(payload)
            return False
        if payload.get("op") == "subscribe":
            self._status.subscribed = bool(payload.get("success"))
            self._status.last_message_at = datetime.now(tz=timezone.utc)
            return True

        topic = str(payload.get("topic", ""))
        if not topic:
            return True
        self._status.last_event_type = topic
        self._status.last_message_at = datetime.now(tz=timezone.utc)
        self._status.messages_processed += 1

        if topic == "order":
            await self.process_order_events(payload)
            return True
        if topic == "execution":
            await self.process_execution_events(payload)
            return True
        if topic == "wallet":
            await self.process_wallet_events(payload)
            return True
        return True

    async def process_order_events(self, payload: dict[str, Any]) -> None:
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            return
        async with self.session_factory() as session:
            for event in rows:
                if not isinstance(event, dict):
                    continue
                await self._persist_execution_event(
                    session,
                    venue="bybit",
                    event_type="order",
                    venue_status=str(event.get("orderStatus", "UNKNOWN")),
                    symbol=str(event.get("symbol")) if event.get("symbol") is not None else None,
                    client_order_id=str(event.get("orderLinkId")) if event.get("orderLinkId") is not None else None,
                    venue_order_id=str(event.get("orderId")) if event.get("orderId") is not None else None,
                    filled_notional=str(event.get("cumExecValue", "0")),
                    average_price=str(event.get("avgPrice")) if event.get("avgPrice") else None,
                    details={"raw_event": event, "topic": "order"},
                )
            await session.commit()

    async def process_execution_events(self, payload: dict[str, Any]) -> None:
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            return
        async with self.session_factory() as session:
            for event in rows:
                if not isinstance(event, dict):
                    continue
                matched_intent = await self._persist_execution_event(
                    session,
                    venue="bybit",
                    event_type="execution",
                    venue_status=str(event.get("orderStatus", "Filled")),
                    symbol=str(event.get("symbol")) if event.get("symbol") is not None else None,
                    client_order_id=str(event.get("orderLinkId")) if event.get("orderLinkId") is not None else None,
                    venue_order_id=str(event.get("orderId")) if event.get("orderId") is not None else None,
                    filled_notional=str(event.get("execValue", "0")),
                    average_price=str(event.get("execPrice")) if event.get("execPrice") else None,
                    details={"raw_event": event, "topic": "execution"},
                )
                quantity = parse_decimal(event.get("execQty"))
                quote_quantity = parse_decimal(event.get("execValue"))
                if quantity > Decimal("0") and quote_quantity > Decimal("0"):
                    await self.account_state_service.apply_execution_trade_delta(
                        session,
                        symbol=str(event.get("symbol", "")).upper(),
                        side=str(event.get("side", "Buy")),
                        execution_intent_id=(
                            int(matched_intent.id) if matched_intent is not None and matched_intent.id is not None else None
                        ),
                        source_strategy=matched_intent.source_strategy if matched_intent is not None else None,
                        client_order_id=str(event.get("orderLinkId")) if event.get("orderLinkId") is not None else None,
                        venue_order_id=str(event.get("orderId")) if event.get("orderId") is not None else None,
                        trade_id=parse_trade_id(event.get("execId")),
                        quantity=quantity,
                        quote_quantity=quote_quantity,
                    )
            await session.commit()

    async def process_wallet_events(self, payload: dict[str, Any]) -> None:
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            return
        coins: list[dict[str, Any]] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            item_coins = item.get("coin", [])
            if isinstance(item_coins, list):
                coins.extend([coin for coin in item_coins if isinstance(coin, dict)])
        if not coins:
            return
        async with self.session_factory() as session:
            await self.account_state_service.apply_wallet_balances(
                session,
                coins,
                free_key="availableToWithdraw",
                locked_key="locked",
                total_key="walletBalance",
                asset_key="coin",
                source_event="wallet",
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
            payload=details,
        )
        return intent


def parse_trade_id(value: object) -> int | None:
    if value is None:
        return None
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:15]
    try:
        return int(digest, 16)
    except ValueError:
        return None
