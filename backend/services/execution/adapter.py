import hashlib
import hmac
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode
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
class BinanceOrderRequest:
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    quantity: str
    price: str
    new_client_order_id: str
    recv_window: int
    timestamp: int

    def signed_payload(self, secret: str) -> dict[str, str | int]:
        payload: dict[str, str | int] = {
            "symbol": self.symbol,
            "side": self.side.upper(),
            "type": self.order_type,
            "timeInForce": self.time_in_force,
            "quantity": self.quantity,
            "price": self.price,
            "newClientOrderId": self.new_client_order_id,
            "recvWindow": self.recv_window,
            "timestamp": self.timestamp,
        }
        query = urlencode(payload)
        signature = hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        payload["signature"] = signature
        return payload


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


class ExecutionTransport(ABC):
    @abstractmethod
    async def submit_binance_order(self, request: BinanceOrderRequest) -> ExecutionDispatch:
        raise NotImplementedError

    @abstractmethod
    async def simulate_fill(
        self,
        intent: ExecutionIntent,
        dispatch: ExecutionDispatch,
    ) -> ExecutionResult:
        raise NotImplementedError


class ExecutionAdapter(ABC):
    @abstractmethod
    async def dispatch(self, intent: ExecutionIntent) -> ExecutionDispatch:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, intent: ExecutionIntent, dispatch: ExecutionDispatch) -> ExecutionResult:
        raise NotImplementedError


class StubBinanceExecutionTransport(ExecutionTransport):
    async def submit_binance_order(self, request: BinanceOrderRequest) -> ExecutionDispatch:
        accepted_at = datetime.now(tz=timezone.utc)
        return ExecutionDispatch(
            client_order_id=request.new_client_order_id,
            venue_order_id=f"binance-stub-{uuid4().hex[:16]}",
            venue="binance",
            venue_status="NEW",
            accepted_at=accepted_at,
            details={
                "transport": "stub",
                "request": asdict(request),
            },
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
            venue_status="FILLED",
            details={
                **dispatch.details,
                "simulated_fill": True,
            },
        )


class BinanceAuthenticatedExecutionTransport(ExecutionTransport):
    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        base_url: str,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.http_transport = http_transport

    async def submit_binance_order(self, request: BinanceOrderRequest) -> ExecutionDispatch:
        payload = request.signed_payload(self.api_secret)
        headers = {"X-MBX-APIKEY": self.api_key}
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=15.0,
            transport=self.http_transport,
        ) as client:
            response = await client.post("/api/v3/order", data=payload, headers=headers)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                try:
                    error_body: object = response.json()
                except ValueError:
                    error_body = response.text
                raise ExecutionTransportError(
                    "binance order submission failed",
                    venue="binance",
                    status_code=response.status_code,
                    response_body=error_body,
                ) from exc
            body = response.json()
        if not isinstance(body, dict):
            raise ValueError("unexpected binance order response")
        accepted_at = datetime.now(tz=timezone.utc)
        return ExecutionDispatch(
            client_order_id=str(body.get("clientOrderId", request.new_client_order_id)),
            venue_order_id=str(body.get("orderId", "")),
            venue="binance",
            venue_status=str(body.get("status", "NEW")),
            accepted_at=accepted_at,
            details={"transport": "authenticated", "response": body},
        )

    async def simulate_fill(
        self,
        intent: ExecutionIntent,
        dispatch: ExecutionDispatch,
    ) -> ExecutionResult:
        raise RuntimeError("authenticated binance transport requires asynchronous venue reconciliation")


class BinanceExecutionAdapter(ExecutionAdapter):
    def __init__(
        self,
        transport: ExecutionTransport | None = None,
        recv_window: int = 5000,
    ) -> None:
        self.transport = transport or StubBinanceExecutionTransport()
        self.recv_window = recv_window

    async def dispatch(self, intent: ExecutionIntent) -> ExecutionDispatch:
        request = self.build_order_request(intent)
        return await self.transport.submit_binance_order(request)

    async def execute(self, intent: ExecutionIntent, dispatch: ExecutionDispatch) -> ExecutionResult:
        return await self.transport.simulate_fill(intent, dispatch)

    def build_order_request(self, intent: ExecutionIntent) -> BinanceOrderRequest:
        timestamp = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        quantity = (intent.approved_notional / intent.entry_price).quantize(
            Decimal("0.00000001"),
            rounding=ROUND_DOWN,
        )
        return BinanceOrderRequest(
            symbol=intent.symbol,
            side=intent.side.upper(),
            order_type="LIMIT",
            time_in_force="GTC",
            quantity=format(quantity, "f"),
            price=format(intent.entry_price, "f"),
            new_client_order_id=self._client_order_id(intent),
            recv_window=self.recv_window,
            timestamp=timestamp,
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
