from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx

from app.models import ExecutionIntent, User
from app.schemas.risk import SignalRiskEvaluateRequest, SignalRiskEvaluateResponse
from services.execution.adapter import (
    BybitAuthenticatedExecutionTransport,
    BybitExecutionAdapter,
    ExecutionTransportError,
    StubBybitExecutionTransport,
)
from services.execution.intent_queue import ExecutionIntentQueueService
from strategies.base import Signal


def build_intent() -> ExecutionIntent:
    user = User(
        id=uuid4(),
        email="owner@example.com",
        password_hash="hash",
        totp_secret=None,
        role="owner",
        created_at=datetime.now(tz=timezone.utc),
    )
    queue = ExecutionIntentQueueService()
    intent = queue.build_intent(
        user=user,
        risk_request=SignalRiskEvaluateRequest(
            signal=Signal(
                symbol="BTCUSDT",
                side="long",
                conviction=0.8,
                source="orderbook_imbalance",
                regime="microstructure",
                suggested_stop=99.0,
                suggested_take_profit=103.0,
            ),
            current_equity=Decimal("10000"),
            entry_price=Decimal("100"),
            proposed_notional=Decimal("500"),
            current_open_positions=0,
            daily_pnl_pct=Decimal("0"),
            leverage=Decimal("1"),
            quote_volume_usd=Decimal("50000000"),
            use_futures=False,
        ),
        risk_response=SignalRiskEvaluateResponse(
            allowed=True,
            reasons=[],
            profile_name="STANDARD",
            recommended_max_notional=Decimal("1000"),
            recommended_risk_amount=Decimal("100"),
            computed_r_multiple=Decimal("3"),
        ),
        notes="ready",
    )
    intent.id = 42
    return intent


def test_bybit_execution_adapter_builds_order_request() -> None:
    adapter = BybitExecutionAdapter(transport=StubBybitExecutionTransport())
    intent = build_intent()

    request = adapter.build_order_request(intent)
    payload = request.payload()

    assert request.symbol == "BTCUSDT"
    assert request.category == "spot"
    assert request.side == "Buy"
    assert request.order_type == "Limit"
    assert request.qty == "5.00000000"
    assert request.order_link_id.startswith("aiq-sim-42-")
    assert payload["timeInForce"] == "GTC"


async def test_bybit_execution_adapter_dispatch_and_execute() -> None:
    adapter = BybitExecutionAdapter(transport=StubBybitExecutionTransport())
    intent = build_intent()

    dispatch = await adapter.dispatch(intent)
    result = await adapter.execute(intent, dispatch)

    assert dispatch.venue == "bybit"
    assert dispatch.venue_status == "New"
    assert result.status == "executed"
    assert result.venue_status == "Filled"
    assert result.client_order_id == dispatch.client_order_id


async def test_bybit_execution_adapter_cancels_dispatched_order() -> None:
    adapter = BybitExecutionAdapter(transport=StubBybitExecutionTransport())
    intent = build_intent()
    intent.client_order_id = "client-42"
    intent.venue_order_id = "venue-42"

    cancelled = await adapter.cancel(intent)

    assert cancelled.status == "cancelled"
    assert cancelled.venue == "bybit"
    assert cancelled.venue_status == "Cancelled"
    assert cancelled.client_order_id == "client-42"
    assert cancelled.venue_order_id == "venue-42"


async def test_authenticated_bybit_transport_submits_signed_order() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "retCode": 0,
                "retMsg": "OK",
                "result": {"orderId": "123456", "orderLinkId": "client-1"},
            },
        )

    transport = BybitAuthenticatedExecutionTransport(
        api_key="api-key",
        api_secret="api-secret",
        base_url="https://api.bybit.com",
        http_transport=httpx.MockTransport(handler),
    )
    request = BybitExecutionAdapter(transport=StubBybitExecutionTransport()).build_order_request(build_intent())

    dispatch = await transport.submit_order(request)

    assert dispatch.venue == "bybit"
    assert dispatch.venue_order_id == "123456"
    assert dispatch.client_order_id == "client-1"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["x-bapi-api-key"] == "api-key"
    assert "\"symbol\":\"BTCUSDT\"" in str(captured["body"])


async def test_authenticated_bybit_transport_raises_on_http_error() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"retCode": 10001, "retMsg": "insufficient balance"})

    transport = BybitAuthenticatedExecutionTransport(
        api_key="api-key",
        api_secret="api-secret",
        base_url="https://api.bybit.com",
        http_transport=httpx.MockTransport(handler),
    )
    request = BybitExecutionAdapter(transport=StubBybitExecutionTransport()).build_order_request(build_intent())

    try:
        await transport.submit_order(request)
    except ExecutionTransportError as exc:
        assert exc.venue == "bybit"
        assert exc.status_code == 400
        assert exc.response_body == {"retCode": 10001, "retMsg": "insufficient balance"}
    else:
        raise AssertionError("expected ExecutionTransportError")


async def test_authenticated_bybit_transport_raises_on_retcode_failure() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"retCode": 10001, "retMsg": "insufficient balance", "result": {}},
        )

    transport = BybitAuthenticatedExecutionTransport(
        api_key="api-key",
        api_secret="api-secret",
        base_url="https://api.bybit.com",
        http_transport=httpx.MockTransport(handler),
    )
    request = BybitExecutionAdapter(transport=StubBybitExecutionTransport()).build_order_request(build_intent())

    try:
        await transport.submit_order(request)
    except ExecutionTransportError as exc:
        assert exc.venue == "bybit"
        assert exc.status_code == 200
        assert exc.response_body == {"retCode": 10001, "retMsg": "insufficient balance", "result": {}}
    else:
        raise AssertionError("expected ExecutionTransportError")


async def test_authenticated_bybit_transport_cancels_order() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "retCode": 0,
                "retMsg": "OK",
                "result": {"orderId": "123456", "orderLinkId": "client-1"},
            },
        )

    transport = BybitAuthenticatedExecutionTransport(
        api_key="api-key",
        api_secret="api-secret",
        base_url="https://api.bybit.com",
        http_transport=httpx.MockTransport(handler),
    )
    intent = build_intent()
    intent.client_order_id = "client-1"
    intent.venue_order_id = "123456"

    cancelled = await transport.cancel_order(intent)

    assert captured["method"] == "POST"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["x-bapi-api-key"] == "api-key"
    assert "\"orderId\":\"123456\"" in str(captured["body"])
    assert cancelled.venue_status == "Cancelled"
    assert cancelled.client_order_id == "client-1"


async def test_authenticated_bybit_transport_raises_on_cancel_retcode_failure() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"retCode": 110001, "retMsg": "order not exists", "result": {}},
        )

    transport = BybitAuthenticatedExecutionTransport(
        api_key="api-key",
        api_secret="api-secret",
        base_url="https://api.bybit.com",
        http_transport=httpx.MockTransport(handler),
    )
    intent = build_intent()
    intent.client_order_id = "client-1"
    intent.venue_order_id = "123456"

    try:
        await transport.cancel_order(intent)
    except ExecutionTransportError as exc:
        assert exc.venue == "bybit"
        assert exc.status_code == 200
        assert exc.response_body == {"retCode": 110001, "retMsg": "order not exists", "result": {}}
    else:
        raise AssertionError("expected ExecutionTransportError")
