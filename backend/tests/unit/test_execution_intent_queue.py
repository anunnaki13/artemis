from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models import ExecutionVenueEvent, User
from app.schemas.risk import SignalRiskEvaluateRequest, SignalRiskEvaluateResponse
from services.execution.intent_queue import ExecutionIntentQueueService
from strategies.base import Signal


class FakeScalarSession:
    def __init__(self, intent: object | None) -> None:
        self.intent = intent
        self.added: list[object] = []
        self._event_id = 1

    async def scalars(self, _query: object) -> "FakeScalarSession":
        return self

    def first(self) -> object | None:
        return self.intent

    async def flush(self) -> None:
        return None

    def add(self, obj: object) -> None:
        if isinstance(obj, ExecutionVenueEvent) and obj.id is None:
            obj.id = self._event_id
            self._event_id += 1
            obj.created_at = datetime.now(tz=timezone.utc)
        self.added.append(obj)


def build_signal_risk_request() -> SignalRiskEvaluateRequest:
    return SignalRiskEvaluateRequest(
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
    )


def build_signal_risk_response() -> SignalRiskEvaluateResponse:
    return SignalRiskEvaluateResponse(
        allowed=True,
        reasons=[],
        profile_name="STANDARD",
        recommended_max_notional=Decimal("1000"),
        recommended_risk_amount=Decimal("100"),
        computed_r_multiple=Decimal("3"),
    )


def test_execution_intent_queue_builds_intent() -> None:
    service = ExecutionIntentQueueService()
    user = User(
        id=uuid4(),
        email="owner@example.com",
        password_hash="hash",
        totp_secret=None,
        role="owner",
        created_at=datetime.now(tz=timezone.utc),
    )
    intent = service.build_intent(
        user=user,
        risk_request=build_signal_risk_request(),
        risk_response=build_signal_risk_response(),
        notes="queue this",
    )

    assert intent.symbol == "BTCUSDT"
    assert intent.status == "queued"
    assert intent.approved_notional == Decimal("500")
    assert intent.signal_payload["source"] == "orderbook_imbalance"


def test_execution_intent_queue_validates_transitions() -> None:
    service = ExecutionIntentQueueService()

    assert service.validate_status_transition("queued", "approved") is True
    assert service.validate_status_transition("approved", "dispatching") is True
    assert service.validate_status_transition("dispatching", "executed") is True
    assert service.validate_status_transition("queued", "executed") is False
    assert service.validate_status_transition("executed", "cancelled") is False


async def test_execution_intent_queue_finds_by_order_id() -> None:
    service = ExecutionIntentQueueService()
    user = User(
        id=uuid4(),
        email="owner@example.com",
        password_hash="hash",
        totp_secret=None,
        role="owner",
        created_at=datetime.now(tz=timezone.utc),
    )
    intent = service.build_intent(
        user=user,
        risk_request=build_signal_risk_request(),
        risk_response=build_signal_risk_response(),
        notes="queue this",
    )
    intent.client_order_id = "paper-client-1"
    intent.venue_order_id = "paper-venue-1"

    found = await service.find_by_order_id(
        FakeScalarSession(intent),  # type: ignore[arg-type]
        client_order_id="paper-client-1",
        venue_order_id=None,
    )

    assert found is intent


async def test_execution_intent_queue_requires_order_identifier() -> None:
    service = ExecutionIntentQueueService()

    try:
        await service.find_by_order_id(
            FakeScalarSession(None),  # type: ignore[arg-type]
            client_order_id=None,
            venue_order_id=None,
        )
    except ValueError as exc:
        assert str(exc) == "client_order_id or venue_order_id is required"
    else:
        raise AssertionError("expected ValueError")


async def test_execution_intent_queue_records_venue_event() -> None:
    service = ExecutionIntentQueueService()
    session = FakeScalarSession(None)

    event = await service.record_venue_event(
        session,  # type: ignore[arg-type]
        execution_intent_id=42,
        venue="binance",
        event_type="executionReport",
        venue_status="PARTIALLY_FILLED",
        symbol="BTCUSDT",
        client_order_id="client-42",
        venue_order_id="venue-42",
        reconcile_state="applied",
        payload={"filled_notional": "250"},
    )

    assert event.id == 1
    assert event.execution_intent_id == 42
    assert event.reconcile_state == "applied"
    assert event.reconciled_at is not None
    assert service.to_venue_event_read(event).venue_status == "PARTIALLY_FILLED"
