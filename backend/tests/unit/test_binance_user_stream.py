from contextlib import AbstractAsyncContextManager
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models import (
    ExecutionIntent,
    ExecutionVenueEvent,
    MarketSnapshot,
    SpotAccountBalance,
    SpotExecutionFill,
    SpotOrderFillState,
    SpotSymbolPosition,
    User,
)
from app.schemas.risk import SignalRiskEvaluateRequest, SignalRiskEvaluateResponse
from services.execution.binance_runtime import BinanceExecutionRuntime
from services.execution.intent_queue import ExecutionIntentQueueService
from services.execution.user_stream import (
    BinanceUserStreamService,
    build_user_stream_signature,
    build_user_stream_subscribe_request,
    compute_average_price,
)
from strategies.base import Signal


class FakeSession:
    def __init__(self, intent: ExecutionIntent | None) -> None:
        self.intent = intent
        self.added: list[object] = []
        self._event_id = 1
        self.committed = False
        self.balances: dict[str, SpotAccountBalance] = {}
        self.fill_states: dict[str, SpotOrderFillState] = {}
        self.market_snapshots: dict[str, MarketSnapshot] = {}
        self.positions: dict[str, SpotSymbolPosition] = {}
        self.fills: list[SpotExecutionFill] = []

    async def scalars(self, _query: object) -> "FakeSession":
        return self

    def first(self) -> ExecutionIntent | None:
        return self.intent

    async def scalar(self, _query: object) -> object | None:
        query_text = str(_query)
        if "spot_order_fill_states" in query_text and self.fill_states:
            return next(iter(self.fill_states.values()))
        if "market_snapshots" in query_text and self.market_snapshots:
            return next(iter(self.market_snapshots.values()))
        return None

    async def get(self, model: type[object], key: object) -> object | None:
        if model is SpotAccountBalance and isinstance(key, str):
            return self.balances.get(key)
        if model is SpotSymbolPosition and isinstance(key, str):
            return self.positions.get(key)
        if model is SpotOrderFillState and isinstance(key, str):
            return self.fill_states.get(key)
        return None

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    def add(self, obj: object) -> None:
        if isinstance(obj, ExecutionVenueEvent) and obj.id is None:
            obj.id = self._event_id
            self._event_id += 1
            obj.created_at = datetime.now(tz=timezone.utc)
        if isinstance(obj, SpotAccountBalance):
            self.balances[obj.asset] = obj
        if isinstance(obj, SpotOrderFillState):
            self.fill_states[obj.order_key] = obj
        if isinstance(obj, SpotExecutionFill):
            self.fills.append(obj)
        if isinstance(obj, SpotSymbolPosition):
            self.positions[obj.symbol] = obj
        self.added.append(obj)


class FakeSessionContext(AbstractAsyncContextManager[FakeSession]):
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


def session_factory(session: FakeSession) -> FakeSessionContext:
    return FakeSessionContext(session)


def build_dispatching_intent() -> ExecutionIntent:
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
    intent.id = 77
    intent.status = "dispatching"
    intent.created_at = datetime.now(tz=timezone.utc)
    intent.updated_at = datetime.now(tz=timezone.utc)
    intent.dispatched_at = datetime.now(tz=timezone.utc)
    intent.client_order_id = "aiq-live-77-abc"
    intent.venue_order_id = "123456"
    intent.execution_venue = "binance"
    return intent


def test_build_user_stream_subscribe_request_signs_payload() -> None:
    runtime = BinanceExecutionRuntime(
        api_key="api-key",
        api_secret="api-secret",
        base_url="https://api.binance.com",
        testnet=False,
        live_transport_enabled=True,
    )
    request = build_user_stream_subscribe_request(runtime, recv_window=5000)

    assert request["method"] == "userDataStream.subscribe.signature"
    params = request["params"]
    assert isinstance(params, dict)
    assert params["apiKey"] == "api-key"
    assert params["recvWindow"] == 5000
    assert params["signature"] == build_user_stream_signature(
        "api-key",
        "api-secret",
        int(params["timestamp"]),
        5000,
    )


def test_compute_average_price_prefers_quote_divided_by_base() -> None:
    assert compute_average_price({"Z": "500", "z": "5", "L": "99"}) == "100"
    assert compute_average_price({"Z": "0", "z": "0", "L": "101.25"}) == "101.25"


async def test_user_stream_processes_filled_execution_report() -> None:
    intent = build_dispatching_intent()
    session = FakeSession(intent)
    session.market_snapshots["BTCUSDT"] = MarketSnapshot(
        symbol="BTCUSDT",
        timestamp=datetime.now(tz=timezone.utc),
        bid_price=None,
        ask_price=None,
        last_price=Decimal("100"),
        funding_rate=None,
        open_interest=None,
        payload=None,
    )
    service = BinanceUserStreamService(
        session_factory=lambda: session_factory(session),
        queue_service=ExecutionIntentQueueService(),
    )

    await service.process_execution_report(
        {
            "e": "executionReport",
            "s": "BTCUSDT",
            "c": "aiq-live-77-abc",
            "i": 123456,
            "x": "TRADE",
            "X": "FILLED",
            "Z": "500",
            "z": "5",
            "r": "NONE",
        },
        subscription_id=9,
    )

    assert session.committed is True
    assert intent.status == "executed"
    assert intent.execution_payload is not None
    assert intent.execution_payload["source"] == "reconciliation"
    event = next(obj for obj in session.added if isinstance(obj, ExecutionVenueEvent))
    assert event.reconcile_state == "applied"
    assert event.execution_intent_id == 77


async def test_user_stream_processes_partial_fill_without_closing_intent() -> None:
    intent = build_dispatching_intent()
    session = FakeSession(intent)
    session.market_snapshots["BTCUSDT"] = MarketSnapshot(
        symbol="BTCUSDT",
        timestamp=datetime.now(tz=timezone.utc),
        bid_price=None,
        ask_price=None,
        last_price=Decimal("100.2"),
        funding_rate=None,
        open_interest=None,
        payload=None,
    )
    service = BinanceUserStreamService(
        session_factory=lambda: session_factory(session),
        queue_service=ExecutionIntentQueueService(),
    )

    await service.process_execution_report(
        {
            "e": "executionReport",
            "s": "BTCUSDT",
            "c": "aiq-live-77-abc",
            "i": 123456,
            "x": "TRADE",
            "X": "PARTIALLY_FILLED",
            "Z": "250",
            "z": "2.5",
            "L": "100.2",
            "r": "NONE",
        },
        subscription_id=11,
    )

    assert session.committed is True
    assert intent.status == "dispatching"
    assert intent.execution_payload is not None
    assert intent.execution_payload["source"] == "venue_event"
    assert intent.execution_payload["venue_status"] == "PARTIALLY_FILLED"


async def test_user_stream_aggregates_trade_events_by_cumulative_fill() -> None:
    session = FakeSession(build_dispatching_intent())
    session.market_snapshots["BTCUSDT"] = MarketSnapshot(
        symbol="BTCUSDT",
        timestamp=datetime.now(tz=timezone.utc),
        bid_price=None,
        ask_price=None,
        last_price=Decimal("65000"),
        funding_rate=None,
        open_interest=None,
        payload=None,
    )
    service = BinanceUserStreamService(
        session_factory=lambda: session_factory(session),
        queue_service=ExecutionIntentQueueService(),
    )

    await service.process_execution_report(
        {
            "e": "executionReport",
            "s": "BTCUSDT",
            "c": "aiq-live-77-abc",
            "i": 123456,
            "x": "TRADE",
            "X": "PARTIALLY_FILLED",
            "S": "BUY",
            "Z": "6500",
            "z": "0.10",
            "L": "65000",
            "t": 1001,
            "r": "NONE",
        },
        subscription_id=12,
    )
    await service.process_execution_report(
        {
            "e": "executionReport",
            "s": "BTCUSDT",
            "c": "aiq-live-77-abc",
            "i": 123456,
            "x": "TRADE",
            "X": "PARTIALLY_FILLED",
            "S": "BUY",
            "Z": "6500",
            "z": "0.10",
            "L": "65000",
            "t": 1001,
            "r": "NONE",
        },
        subscription_id=12,
    )
    await service.process_execution_report(
        {
            "e": "executionReport",
            "s": "BTCUSDT",
            "c": "aiq-live-77-abc",
            "i": 123456,
            "x": "TRADE",
            "X": "PARTIALLY_FILLED",
            "S": "BUY",
            "Z": "9750",
            "z": "0.15",
            "L": "65000",
            "t": 1002,
            "r": "NONE",
        },
        subscription_id=12,
    )

    position = session.positions["BTCUSDT"]
    assert position.net_quantity == Decimal("0.15")
    assert position.quote_exposure_usd == Decimal("9750")
    assert len(session.fills) == 2
    assert session.fills[0].execution_intent_id == 77
    assert session.fills[0].source_strategy == "orderbook_imbalance"


async def test_user_stream_processes_outbound_account_position() -> None:
    session = FakeSession(None)
    service = BinanceUserStreamService(
        session_factory=lambda: session_factory(session),
        queue_service=ExecutionIntentQueueService(),
    )

    await service.process_outbound_account_position(
        {
            "e": "outboundAccountPosition",
            "B": [
                {"a": "USDT", "f": "250.0", "l": "10.0"},
                {"a": "BNB", "f": "1.5", "l": "0.0"},
            ],
        }
    )

    assert session.committed is True
    assert session.balances["USDT"].total == Decimal("260.0")
    assert session.balances["USDT"].total_value_usd == Decimal("260.0")


async def test_user_stream_processes_balance_update() -> None:
    session = FakeSession(None)
    service = BinanceUserStreamService(
        session_factory=lambda: session_factory(session),
        queue_service=ExecutionIntentQueueService(),
    )

    await service.process_balance_update(
        {
            "e": "balanceUpdate",
            "a": "USDT",
            "d": "12.5",
        }
    )

    assert session.committed is True
    assert session.balances["USDT"].free == Decimal("12.5")
    assert session.balances["USDT"].last_delta == Decimal("12.5")
