import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Mapping
from uuid import uuid4

import httpx

from app.config import get_settings
from app.models import ExecutionIntent


class ExecutionTransportError(Exception):
    def __init__(
        self,
        message: str,
        *,
        venue: str,
        status_code: int | None = None,
        response_body: object | None = None,
    ) -> None:
        super().__init__(message)
        self.venue = venue
        self.status_code = status_code
        self.response_body = response_body


@dataclass(frozen=True)
class BybitOrderRequest:
    category: str
    symbol: str
    side: str
    order_type: str
    qty: str
    price: str
    order_link_id: str
    time_in_force: str

    def payload(self) -> dict[str, str]:
        return {
            "category": self.category,
            "symbol": self.symbol,
            "side": self.side,
            "orderType": self.order_type,
            "qty": self.qty,
            "price": self.price,
            "orderLinkId": self.order_link_id,
            "timeInForce": self.time_in_force,
        }


@dataclass(frozen=True)
class ExecutionDispatch:
    client_order_id: str
    venue_order_id: str
    venue: str
    venue_status: str
    accepted_at: datetime
    details: dict[str, object]


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    filled_notional: Decimal
    average_price: Decimal
    executed_at: datetime
    venue: str
    client_order_id: str
    venue_order_id: str
    venue_status: str
    details: dict[str, object]


@dataclass(frozen=True)
class ExecutionCancel:
    status: str
    cancelled_at: datetime
    venue: str
    client_order_id: str | None
    venue_order_id: str | None
    venue_status: str
    details: dict[str, object]


class ExecutionTransport(ABC):
    @abstractmethod
    async def submit_order(self, request: BybitOrderRequest) -> ExecutionDispatch:
        raise NotImplementedError

    @abstractmethod
    async def simulate_fill(
        self,
        intent: ExecutionIntent,
        dispatch: ExecutionDispatch,
    ) -> ExecutionResult:
        raise NotImplementedError

    @abstractmethod
    async def cancel_order(self, intent: ExecutionIntent) -> ExecutionCancel:
        raise NotImplementedError


class ExecutionAdapter(ABC):
    @abstractmethod
    async def dispatch(self, intent: ExecutionIntent) -> ExecutionDispatch:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, intent: ExecutionIntent, dispatch: ExecutionDispatch) -> ExecutionResult:
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, intent: ExecutionIntent) -> ExecutionCancel:
        raise NotImplementedError


class StubBybitExecutionTransport(ExecutionTransport):
    async def submit_order(self, request: BybitOrderRequest) -> ExecutionDispatch:
        accepted_at = datetime.now(tz=timezone.utc)
        return ExecutionDispatch(
            client_order_id=request.order_link_id,
            venue_order_id=f"bybit-stub-{uuid4().hex[:16]}",
            venue="bybit",
            venue_status="New",
            accepted_at=accepted_at,
            details={"transport": "stub", "request": request.payload()},
        )

    async def simulate_fill(
        self,
        intent: ExecutionIntent,
        dispatch: ExecutionDispatch,
    ) -> ExecutionResult:
        executed_at = datetime.now(tz=timezone.utc)
        return ExecutionResult(
            status="executed",
            filled_notional=intent.approved_notional,
            average_price=intent.entry_price,
            executed_at=executed_at,
            venue=dispatch.venue,
            client_order_id=dispatch.client_order_id,
            venue_order_id=dispatch.venue_order_id,
            venue_status="Filled",
            details={**dispatch.details, "simulated_fill": True},
        )

    async def cancel_order(self, intent: ExecutionIntent) -> ExecutionCancel:
        return ExecutionCancel(
            status="cancelled",
            cancelled_at=datetime.now(tz=timezone.utc),
            venue="bybit",
            client_order_id=intent.client_order_id,
            venue_order_id=intent.venue_order_id,
            venue_status="Cancelled",
            details={"transport": "stub", "simulated_cancel": True},
        )


class BybitAuthenticatedExecutionTransport(ExecutionTransport):
    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        base_url: str,
        recv_window: int = 5000,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.http_transport = http_transport

    def _sign(self, timestamp: int, payload: Mapping[str, object]) -> tuple[str, str]:
        body = json.dumps(dict(payload), separators=(",", ":"), sort_keys=True)
        sign_payload = f"{timestamp}{self.api_key}{self.recv_window}{body}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            sign_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature, body

    def _validate_success_payload(
        self,
        payload_response: object,
        *,
        action: str,
        status_code: int,
    ) -> dict[str, object]:
        if not isinstance(payload_response, dict):
            raise ValueError(f"unexpected bybit {action} response")
        ret_code = payload_response.get("retCode", 0)
        try:
            normalized_ret_code = int(ret_code)
        except (TypeError, ValueError):
            normalized_ret_code = -1
        if normalized_ret_code != 0:
            raise ExecutionTransportError(
                f"bybit {action} failed",
                venue="bybit",
                status_code=status_code,
                response_body=payload_response,
            )
        result = payload_response.get("result", {})
        if not isinstance(result, dict):
            raise ValueError(f"unexpected bybit {action} result")
        return result

    async def submit_order(self, request: BybitOrderRequest) -> ExecutionDispatch:
        timestamp = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        payload = request.payload()
        signature, body = self._sign(timestamp, payload)
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": str(self.recv_window),
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=15.0,
            transport=self.http_transport,
        ) as client:
            try:
                response = await client.post("/v5/order/create", content=body, headers=headers)
            except httpx.RequestError as exc:
                raise ExecutionTransportError(
                    "bybit order submission transport error",
                    venue="bybit",
                    response_body={"retMsg": str(exc), "transport_error": exc.__class__.__name__},
                ) from exc
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                try:
                    error_body: object = response.json()
                except ValueError:
                    error_body = response.text
                raise ExecutionTransportError(
                    "bybit order submission failed",
                    venue="bybit",
                    status_code=response.status_code,
                    response_body=error_body,
                ) from exc
            payload_response = response.json()
        result = self._validate_success_payload(
            payload_response,
            action="order submission",
            status_code=response.status_code,
        )
        return ExecutionDispatch(
            client_order_id=str(result.get("orderLinkId", request.order_link_id)),
            venue_order_id=str(result.get("orderId", "")),
            venue="bybit",
            venue_status=str(result.get("orderStatus", "New")),
            accepted_at=datetime.now(tz=timezone.utc),
            details={"transport": "authenticated", "response": payload_response},
        )

    async def simulate_fill(
        self,
        intent: ExecutionIntent,
        dispatch: ExecutionDispatch,
    ) -> ExecutionResult:
        raise RuntimeError("authenticated bybit transport requires asynchronous venue reconciliation")

    async def cancel_order(self, intent: ExecutionIntent) -> ExecutionCancel:
        timestamp = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        payload: dict[str, object] = {
            "category": "spot",
            "symbol": intent.symbol,
        }
        if intent.venue_order_id:
            payload["orderId"] = intent.venue_order_id
        elif intent.client_order_id:
            payload["orderLinkId"] = intent.client_order_id
        else:
            raise ValueError("dispatching intent is missing client_order_id and venue_order_id")
        signature, body = self._sign(timestamp, payload)
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": str(self.recv_window),
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=15.0,
            transport=self.http_transport,
        ) as client:
            try:
                response = await client.post("/v5/order/cancel", content=body, headers=headers)
            except httpx.RequestError as exc:
                raise ExecutionTransportError(
                    "bybit order cancellation transport error",
                    venue="bybit",
                    response_body={"retMsg": str(exc), "transport_error": exc.__class__.__name__},
                ) from exc
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                try:
                    error_body: object = response.json()
                except ValueError:
                    error_body = response.text
                raise ExecutionTransportError(
                    "bybit order cancellation failed",
                    venue="bybit",
                    status_code=response.status_code,
                    response_body=error_body,
                ) from exc
            payload_response = response.json()
        result = self._validate_success_payload(
            payload_response,
            action="order cancellation",
            status_code=response.status_code,
        )
        return ExecutionCancel(
            status="cancelled",
            cancelled_at=datetime.now(tz=timezone.utc),
            venue="bybit",
            client_order_id=str(result.get("orderLinkId", intent.client_order_id or "")) or intent.client_order_id,
            venue_order_id=str(result.get("orderId", intent.venue_order_id or "")) or intent.venue_order_id,
            venue_status=str(result.get("orderStatus", "Cancelled")),
            details={"transport": "authenticated", "response": payload_response},
        )


class BybitExecutionAdapter(ExecutionAdapter):
    def __init__(
        self,
        transport: ExecutionTransport | None = None,
    ) -> None:
        self.transport = transport or StubBybitExecutionTransport()

    async def dispatch(self, intent: ExecutionIntent) -> ExecutionDispatch:
        request = self.build_order_request(intent)
        return await self.transport.submit_order(request)

    async def execute(self, intent: ExecutionIntent, dispatch: ExecutionDispatch) -> ExecutionResult:
        return await self.transport.simulate_fill(intent, dispatch)

    async def cancel(self, intent: ExecutionIntent) -> ExecutionCancel:
        return await self.transport.cancel_order(intent)

    def build_order_request(self, intent: ExecutionIntent) -> BybitOrderRequest:
        quantity = (intent.approved_notional / intent.entry_price).quantize(
            Decimal("0.00000001"),
            rounding=ROUND_DOWN,
        )
        normalized_side = intent.side.strip().lower()
        if normalized_side in {"buy", "long"}:
            side = "Buy"
        elif normalized_side in {"sell", "short"}:
            side = "Sell"
        else:
            raise ValueError(f"unsupported execution side: {intent.side}")
        return BybitOrderRequest(
            category="spot",
            symbol=intent.symbol,
            side=side,
            order_type="Limit",
            qty=format(quantity, "f"),
            price=format(intent.entry_price, "f"),
            order_link_id=self._client_order_id(intent),
            time_in_force="GTC",
        )

    def _client_order_id(self, intent: ExecutionIntent) -> str:
        settings = get_settings()
        prefix = "aiq-live" if settings.mode in {"live_micro", "live_scaled"} else "aiq-sim"
        return f"{prefix}-{intent.id or 'pending'}-{uuid4().hex[:12]}"


class PaperExecutionAdapter(ExecutionAdapter):
    async def dispatch(self, intent: ExecutionIntent) -> ExecutionDispatch:
        accepted_at = datetime.now(tz=timezone.utc)
        client_order_id = f"paper-{intent.id or 'pending'}-{uuid4().hex[:12]}"
        venue_order_id = f"paper-fill-{uuid4().hex[:16]}"
        return ExecutionDispatch(
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
            venue="paper",
            venue_status="accepted",
            accepted_at=accepted_at,
            details={
                "mode": "paper",
                "symbol": intent.symbol,
                "side": intent.side,
                "source_strategy": intent.source_strategy,
            },
        )

    async def execute(self, intent: ExecutionIntent, dispatch: ExecutionDispatch) -> ExecutionResult:
        executed_at = datetime.now(tz=timezone.utc)
        return ExecutionResult(
            status="executed",
            filled_notional=intent.approved_notional,
            average_price=intent.entry_price,
            executed_at=executed_at,
            venue=dispatch.venue,
            client_order_id=dispatch.client_order_id,
            venue_order_id=dispatch.venue_order_id,
            venue_status="filled",
            details={
                **dispatch.details,
                "accepted_at": dispatch.accepted_at.isoformat(),
            },
        )

    async def cancel(self, intent: ExecutionIntent) -> ExecutionCancel:
        return ExecutionCancel(
            status="cancelled",
            cancelled_at=datetime.now(tz=timezone.utc),
            venue="paper",
            client_order_id=intent.client_order_id,
            venue_order_id=intent.venue_order_id,
            venue_status="CANCELED",
            details={"mode": "paper", "source": "cancel"},
        )
