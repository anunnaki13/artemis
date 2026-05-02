from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.models import ExecutionIntent, ExecutionVenueEvent, User
from app.schemas.risk import SignalRiskEvaluateRequest, SignalRiskEvaluateResponse
from services.execution.intent_queue import ExecutionIntentQueueService
from services.execution.adapter import ExecutionTransportError
from services.execution.worker import ExecutionWorkerService
from strategies.base import Signal


class FakeSession:
    def __init__(self, intent: ExecutionIntent | None) -> None:
        self.intent = intent
        self.added: list[object] = []
        self._event_id = 100

    async def scalars(self, _query: object) -> "FakeSession":
        return self

    def first(self) -> ExecutionIntent | None:
        return self.intent

    async def flush(self) -> None:
        return None

    def add(self, obj: object) -> None:
        if isinstance(obj, ExecutionVenueEvent) and obj.id is None:
            obj.id = self._event_id
            self._event_id += 1
        self.added.append(obj)
        return None


class FakeScalarListSession:
    def __init__(self, intents: list[ExecutionIntent]) -> None:
        self.intents = intents
        self.added: list[object] = []

    async def scalars(self, _query: object) -> "FakeScalarListSession":
        return self

    def first(self) -> ExecutionIntent | None:
        return self.intents[0] if self.intents else None

    def all(self) -> list[ExecutionIntent]:
        return self.intents

    async def flush(self) -> None:
        return None

    def add(self, obj: object) -> None:
        self.added.append(obj)
        return None


class FailingAdapter:
    async def dispatch(self, _intent: ExecutionIntent) -> object:
        raise ExecutionTransportError(
            "venue rejected order",
            venue="bybit",
            status_code=200,
            response_body={"retCode": 10001, "retMsg": "insufficient balance"},
        )

    async def execute(self, _intent: ExecutionIntent, _dispatch: object) -> object:
        raise AssertionError("execute should not be called")

    async def cancel(self, _intent: ExecutionIntent) -> object:
        raise AssertionError("cancel should not be called")


def build_approved_intent() -> ExecutionIntent:
    user = User(
        id=uuid4(),
        email="owner@example.com",
        password_hash="hash",
        totp_secret=None,
        role="owner",
        created_at=datetime.now(tz=timezone.utc),
    )
    queue = ExecutionIntentQueueService()
    return queue.build_intent(
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


async def test_execution_worker_dispatches_approved_intent() -> None:
    intent = build_approved_intent()
    intent.id = 1
    intent.status = "approved"
    intent.created_at = datetime.now(tz=timezone.utc)
    intent.updated_at = datetime.now(tz=timezone.utc)
    session = FakeSession(intent)

    worker = ExecutionWorkerService(ExecutionIntentQueueService())
    dispatched = await worker.dispatch_next(session)  # type: ignore[arg-type]

    assert dispatched is not None
    assert dispatched.status == "executed"
    assert dispatched.client_order_id is not None
    assert dispatched.venue_order_id is not None
    assert dispatched.execution_venue == "paper"
    assert dispatched.execution_payload is not None
    assert dispatched.execution_payload["venue"] == "paper"


async def test_execution_worker_reconciles_dispatching_intent() -> None:
    intent = build_approved_intent()
    intent.id = 2
    intent.status = "dispatching"
    intent.created_at = datetime.now(tz=timezone.utc)
    intent.updated_at = datetime.now(tz=timezone.utc)
    intent.dispatched_at = datetime.now(tz=timezone.utc)
    session = FakeSession(intent)

    worker = ExecutionWorkerService(ExecutionIntentQueueService())
    reconciled = await worker.reconcile(
        session,  # type: ignore[arg-type]
        intent=intent,
        status="executed",
        filled_notional="500",
        average_price="100",
        venue="paper",
        venue_order_id="paper-fill-1",
        client_order_id="paper-client-1",
        details={"source": "test"},
    )

    assert reconciled.status == "executed"
    assert reconciled.client_order_id == "paper-client-1"
    assert reconciled.venue_order_id == "paper-fill-1"
    assert reconciled.execution_payload is not None
    assert reconciled.execution_payload["source"] == "reconciliation"


async def test_execution_worker_fails_stale_dispatches() -> None:
    intent = build_approved_intent()
    intent.id = 3
    intent.status = "dispatching"
    intent.created_at = datetime.now(tz=timezone.utc)
    intent.updated_at = datetime.now(tz=timezone.utc)
    intent.dispatched_at = datetime.now(tz=timezone.utc) - timedelta(seconds=120)
    session = FakeScalarListSession([intent])

    worker = ExecutionWorkerService(ExecutionIntentQueueService(), dispatch_timeout_seconds=30)
    failed = await worker.fail_stale_dispatches(session)  # type: ignore[arg-type]

    assert len(failed) == 1
    assert failed[0].status == "failed"
    assert failed[0].execution_payload is not None
    assert failed[0].execution_payload["reason"] == "dispatch timeout"


async def test_execution_worker_applies_partial_fill_event_without_closing_intent() -> None:
    intent = build_approved_intent()
    intent.id = 4
    intent.status = "dispatching"
    intent.created_at = datetime.now(tz=timezone.utc)
    intent.updated_at = datetime.now(tz=timezone.utc)
    intent.dispatched_at = datetime.now(tz=timezone.utc)
    session = FakeSession(intent)

    worker = ExecutionWorkerService(ExecutionIntentQueueService())
    updated, reconcile_state = await worker.apply_venue_event(
        session,  # type: ignore[arg-type]
        intent=intent,
        venue="bybit",
        event_type="execution",
        venue_status="PARTIALLY_FILLED",
        filled_notional="250",
        average_price="100.5",
        venue_order_id="bybit-order-1",
        client_order_id="bybit-client-1",
        details={"last_executed_qty": "2.5"},
    )

    assert reconcile_state == "applied"
    assert updated.status == "dispatching"
    assert updated.execution_payload is not None
    assert updated.execution_payload["venue_status"] == "PARTIALLY_FILLED"
    assert updated.execution_payload["source"] == "venue_event"


async def test_execution_worker_maps_filled_venue_event_to_executed() -> None:
    intent = build_approved_intent()
    intent.id = 5
    intent.status = "dispatching"
    intent.created_at = datetime.now(tz=timezone.utc)
    intent.updated_at = datetime.now(tz=timezone.utc)
    intent.dispatched_at = datetime.now(tz=timezone.utc)
    session = FakeSession(intent)

    worker = ExecutionWorkerService(ExecutionIntentQueueService())
    updated, reconcile_state = await worker.apply_venue_event(
        session,  # type: ignore[arg-type]
        intent=intent,
        venue="bybit",
        event_type="execution",
        venue_status="FILLED",
        filled_notional="500",
        average_price="100",
        venue_order_id="bybit-order-2",
        client_order_id="bybit-client-2",
        details={"trade_count": 3},
    )

    assert reconcile_state == "applied"


async def test_execution_worker_persists_bybit_error_diagnostics() -> None:
    intent = build_approved_intent()
    intent.id = 6
    intent.status = "approved"
    intent.created_at = datetime.now(tz=timezone.utc)
    intent.updated_at = datetime.now(tz=timezone.utc)
    session = FakeSession(intent)

    worker = ExecutionWorkerService(ExecutionIntentQueueService(), adapter=FailingAdapter())  # type: ignore[arg-type]
    failed = await worker.dispatch_next(session)  # type: ignore[arg-type]

    assert failed is not None
    assert failed.status == "failed"
    assert failed.execution_payload is not None
    assert failed.execution_payload["ret_code"] == 10001
    assert failed.execution_payload["ret_msg"] == "insufficient balance"
    assert failed.execution_payload["incident_type"] == "insufficient_balance"
    assert failed.execution_payload["suggested_action"] == "reduce_size"
    assert failed.execution_payload["retryable"] is False


async def test_execution_worker_cancels_dispatching_intent() -> None:
    intent = build_approved_intent()
    intent.id = 6
    intent.status = "dispatching"
    intent.created_at = datetime.now(tz=timezone.utc)
    intent.updated_at = datetime.now(tz=timezone.utc)
    intent.dispatched_at = datetime.now(tz=timezone.utc)
    intent.client_order_id = "paper-client-6"
    intent.venue_order_id = "paper-order-6"
    intent.execution_venue = "paper"
    session = FakeSession(intent)

    worker = ExecutionWorkerService(ExecutionIntentQueueService())
    cancelled = await worker.request_cancel(
        session,  # type: ignore[arg-type]
        intent=intent,
        reason="operator abort",
    )

    assert cancelled.status == "cancelled"
    assert cancelled.cancelled_at is not None
    assert cancelled.execution_payload is not None
    assert cancelled.execution_payload["source"] == "venue_cancel"
    assert cancelled.execution_payload["venue_status"] == "CANCELED"
