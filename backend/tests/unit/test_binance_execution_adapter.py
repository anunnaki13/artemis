from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx

from app.models import ExecutionIntent
from app.models import User
from app.schemas.risk import SignalRiskEvaluateRequest, SignalRiskEvaluateResponse
from services.execution.adapter import (
    BinanceAuthenticatedExecutionTransport,
    BinanceExecutionAdapter,
    ExecutionTransportError,
    StubBinanceExecutionTransport,
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


def test_binance_execution_adapter_builds_order_request() -> None:
    adapter = BinanceExecutionAdapter(transport=StubBinanceExecutionTransport())
    intent = build_intent()

    request = adapter.build_order_request(intent)
    signed = request.signed_payload("secret")

    assert request.symbol == "BTCUSDT"
    assert request.side == "LONG"
    assert request.order_type == "LIMIT"
    assert request.quantity == "5.00000000"
    assert request.new_client_order_id.startswith("aiq-sim-42-")
    assert isinstance(signed["signature"], str)


async def test_binance_execution_adapter_dispatch_and_execute() -> None:
    adapter = BinanceExecutionAdapter(transport=StubBinanceExecutionTransport())
    intent = build_intent()

    dispatch = await adapter.dispatch(intent)
    result = await adapter.execute(intent, dispatch)

    assert dispatch.venue == "binance"
    assert dispatch.venue_status == "NEW"
    assert result.status == "executed"
    assert result.venue_status == "FILLED"
    assert result.client_order_id == dispatch.client_order_id


async def test_authenticated_binance_transport_submits_signed_order() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        body = request.content.decode("utf-8")
        captured["body"] = body
        return httpx.Response(
            200,
            json={
                "symbol": "BTCUSDT",
                "orderId": "123456",
                "clientOrderId": "client-1",
                "status": "NEW",
            },
        )

    transport = BinanceAuthenticatedExecutionTransport(
        api_key="api-key",
        api_secret="api-secret",
        base_url="https://api.binance.com",
        http_transport=httpx.MockTransport(handler),
    )
    request = BinanceExecutionAdapter(transport=StubBinanceExecutionTransport()).build_order_request(build_intent())

    dispatch = await transport.submit_binance_order(request)

    assert dispatch.venue == "binance"
    assert dispatch.venue_order_id == "123456"
    assert dispatch.client_order_id == "client-1"
    assert "signature=" in str(captured["body"])
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["x-mbx-apikey"] == "api-key"


async def test_authenticated_binance_transport_raises_on_http_error() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": -2010, "msg": "Account has insufficient balance"})

    transport = BinanceAuthenticatedExecutionTransport(
        api_key="api-key",
        api_secret="api-secret",
        base_url="https://api.binance.com",
        http_transport=httpx.MockTransport(handler),
    )
    request = BinanceExecutionAdapter(transport=StubBinanceExecutionTransport()).build_order_request(build_intent())

    try:
        await transport.submit_binance_order(request)
    except ExecutionTransportError as exc:
        assert exc.venue == "binance"
        assert exc.status_code == 400
        assert exc.response_body == {"code": -2010, "msg": "Account has insufficient balance"}
    else:
        raise AssertionError("expected ExecutionTransportError")
