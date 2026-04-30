from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import get_current_user
from app.models import ExecutionIntent, User
from app.schemas.execution import (
    BinanceExecutionPreviewResponse,
    ExecutionDispatchResponse,
    ExecutionIntentRead,
    ExecutionOrderReconcileRequest,
    ExecutionReconcileRequest,
    ExecutionIntentStatusUpdateRequest,
    ExecutionIntentSubmitRequest,
    ExecutionIntentSubmitResponse,
    ExecutionTimeoutSweepResponse,
    ExecutionVenueEventIngestRequest,
    ExecutionVenueEventIngestResponse,
    VenueEventState,
)
from app.schemas.risk import SignalRiskEvaluateResponse
from services.execution.adapter import (
    BinanceAuthenticatedExecutionTransport,
    BinanceExecutionAdapter,
    PaperExecutionAdapter,
    StubBinanceExecutionTransport,
)
from services.execution.binance_runtime import resolve_binance_execution_runtime
from services.execution.intent_queue import ExecutionIntentQueueService
from services.execution.worker import ExecutionWorkerService
from services.risk.capital_profile import CapitalProfileManager
from services.risk.signal_gate import SignalRiskGate, SignalRiskInput

router = APIRouter(prefix="/execution", tags=["execution"])
intent_queue_service = ExecutionIntentQueueService()


def evaluate_signal_risk(payload: ExecutionIntentSubmitRequest) -> SignalRiskEvaluateResponse:
    settings = get_settings()
    capital_profile = CapitalProfileManager(settings.capital_profiles_path).evaluate(
        payload.signal_risk.current_equity
    )
    decision = SignalRiskGate().evaluate(
        SignalRiskInput(
            signal=payload.signal_risk.signal,
            current_equity=payload.signal_risk.current_equity,
            entry_price=payload.signal_risk.entry_price,
            proposed_notional=payload.signal_risk.proposed_notional,
            current_open_positions=payload.signal_risk.current_open_positions,
            daily_pnl_pct=payload.signal_risk.daily_pnl_pct,
            leverage=payload.signal_risk.leverage,
            quote_volume_usd=payload.signal_risk.quote_volume_usd,
            use_futures=payload.signal_risk.use_futures,
        ),
        capital_profile,
    )
    return SignalRiskEvaluateResponse(
        allowed=decision.allowed,
        reasons=decision.reasons,
        profile_name=decision.profile_name,
        recommended_max_notional=decision.recommended_max_notional,
        recommended_risk_amount=decision.recommended_risk_amount,
        computed_r_multiple=decision.computed_r_multiple,
    )


async def build_execution_worker(session: AsyncSession) -> ExecutionWorkerService:
    settings = get_settings()
    if settings.mode in {"live_micro", "live_scaled"}:
        runtime = await resolve_binance_execution_runtime(session)
        if runtime.live_transport_enabled:
            adapter = BinanceExecutionAdapter(
                transport=BinanceAuthenticatedExecutionTransport(
                    api_key=runtime.api_key,
                    api_secret=runtime.api_secret,
                    base_url=runtime.base_url,
                )
            )
        else:
            adapter = BinanceExecutionAdapter(transport=StubBinanceExecutionTransport())
        return ExecutionWorkerService(intent_queue_service, adapter=adapter)
    return ExecutionWorkerService(intent_queue_service, adapter=PaperExecutionAdapter())


@router.post("/intents/submit", response_model=ExecutionIntentSubmitResponse)
async def submit_execution_intent(
    payload: ExecutionIntentSubmitRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionIntentSubmitResponse:
    risk = evaluate_signal_risk(payload)
    if not risk.allowed:
        return ExecutionIntentSubmitResponse(queued=False, risk=risk, intent=None)

    intent = await intent_queue_service.enqueue(
        session,
        user=user,
        risk_request=payload.signal_risk,
        risk_response=risk,
        notes=payload.notes,
    )
    await session.commit()
    return ExecutionIntentSubmitResponse(
        queued=True,
        risk=risk,
        intent=intent_queue_service.to_read(intent),
    )


@router.get("/intents", response_model=list[ExecutionIntentRead])
async def list_execution_intents(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ExecutionIntentRead]:
    query = select(ExecutionIntent).order_by(ExecutionIntent.created_at.desc()).limit(limit)
    if status_filter is not None:
        query = query.where(ExecutionIntent.status == status_filter)
    intents = list((await session.scalars(query)).all())
    return [intent_queue_service.to_read(intent) for intent in intents]


@router.get("/intents/by-order-id", response_model=ExecutionIntentRead)
async def get_execution_intent_by_order_id(
    client_order_id: str | None = Query(default=None, max_length=128),
    venue_order_id: str | None = Query(default=None, max_length=128),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionIntentRead:
    try:
        intent = await intent_queue_service.find_by_order_id(
            session,
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execution intent not found")
    return intent_queue_service.to_read(intent)


@router.get("/venues/binance/intents/{intent_id}/preview-order", response_model=BinanceExecutionPreviewResponse)
async def preview_binance_order_request(
    intent_id: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BinanceExecutionPreviewResponse:
    intent = await session.get(ExecutionIntent, intent_id)
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execution intent not found")
    try:
        runtime = await resolve_binance_execution_runtime(session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    adapter = BinanceExecutionAdapter()
    request = adapter.build_order_request(intent)
    signed_payload = request.signed_payload(runtime.api_secret)
    unsigned_payload = {key: value for key, value in signed_payload.items() if key != "signature"}
    return BinanceExecutionPreviewResponse(
        symbol=intent.symbol,
        side=intent.side,
        base_url=runtime.base_url,
        testnet=runtime.testnet,
        live_transport_enabled=runtime.live_transport_enabled,
        transport_mode="authenticated" if runtime.live_transport_enabled else "stub",
        client_order_id=request.new_client_order_id,
        unsigned_payload=unsigned_payload,
        signed_payload_keys=sorted(signed_payload.keys()),
    )


@router.post("/intents/{intent_id}/status", response_model=ExecutionIntentRead)
async def update_execution_intent_status(
    intent_id: int,
    payload: ExecutionIntentStatusUpdateRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionIntentRead:
    intent = await session.get(ExecutionIntent, intent_id)
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execution intent not found")
    if not intent_queue_service.validate_status_transition(intent.status, payload.status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid status transition from {intent.status} to {payload.status}",
        )
    intent = await intent_queue_service.update_status(
        session,
        intent=intent,
        status=payload.status,
        notes=payload.notes,
    )
    await session.commit()
    return intent_queue_service.to_read(intent)


@router.post("/intents/{intent_id}/reconcile", response_model=ExecutionIntentRead)
async def reconcile_execution_intent(
    intent_id: int,
    payload: ExecutionReconcileRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionIntentRead:
    intent = await session.get(ExecutionIntent, intent_id)
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execution intent not found")
    if intent.status != "dispatching":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"reconciliation requires dispatching status, got {intent.status}",
        )
    worker = await build_execution_worker(session)
    intent = await worker.reconcile(
        session,
        intent=intent,
        status=payload.status,
        filled_notional=str(payload.filled_notional),
        average_price=str(payload.average_price),
        venue=payload.venue,
        venue_order_id=payload.venue_order_id,
        client_order_id=payload.client_order_id,
        details=payload.details,
    )
    await session.commit()
    return intent_queue_service.to_read(intent)


@router.post("/reconcile/by-order-id", response_model=ExecutionIntentRead)
async def reconcile_execution_intent_by_order_id(
    payload: ExecutionOrderReconcileRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionIntentRead:
    try:
        intent = await intent_queue_service.find_by_order_id(
            session,
            client_order_id=payload.client_order_id,
            venue_order_id=payload.venue_order_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execution intent not found")
    if intent.status != "dispatching":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"reconciliation requires dispatching status, got {intent.status}",
        )
    worker = await build_execution_worker(session)
    intent = await worker.reconcile(
        session,
        intent=intent,
        status=payload.status,
        filled_notional=str(payload.filled_notional),
        average_price=str(payload.average_price),
        venue=payload.venue,
        venue_order_id=payload.venue_order_id,
        client_order_id=payload.client_order_id,
        details=payload.details,
    )
    await session.commit()
    return intent_queue_service.to_read(intent)


@router.post("/venues/events/ingest", response_model=ExecutionVenueEventIngestResponse)
async def ingest_execution_venue_event(
    payload: ExecutionVenueEventIngestRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionVenueEventIngestResponse:
    intent = await intent_queue_service.find_by_order_id(
        session,
        client_order_id=payload.client_order_id,
        venue_order_id=payload.venue_order_id,
    )
    worker = await build_execution_worker(session)
    reconcile_state: VenueEventState = "unmatched"
    if intent is not None:
        intent, reconcile_state = await worker.apply_venue_event(
            session,
            intent=intent,
            venue=payload.venue,
            event_type=payload.event_type,
            venue_status=payload.venue_status,
            filled_notional=str(payload.filled_notional) if payload.filled_notional is not None else None,
            average_price=str(payload.average_price) if payload.average_price is not None else None,
            venue_order_id=payload.venue_order_id,
            client_order_id=payload.client_order_id,
            details=payload.details,
        )
    event = await intent_queue_service.record_venue_event(
        session,
        execution_intent_id=int(intent.id) if intent is not None and intent.id is not None else None,
        venue=payload.venue,
        event_type=payload.event_type,
        venue_status=payload.venue_status,
        symbol=payload.symbol,
        client_order_id=payload.client_order_id,
        venue_order_id=payload.venue_order_id,
        reconcile_state=reconcile_state,
        payload={
            "symbol": payload.symbol,
            "filled_notional": str(payload.filled_notional) if payload.filled_notional is not None else None,
            "average_price": str(payload.average_price) if payload.average_price is not None else None,
            "details": payload.details,
        },
    )
    await session.commit()
    return ExecutionVenueEventIngestResponse(
        matched=intent is not None,
        event=intent_queue_service.to_venue_event_read(event),
        intent=intent_queue_service.to_read(intent) if intent is not None else None,
    )


@router.post("/worker/dispatch-next", response_model=ExecutionDispatchResponse)
async def dispatch_next_execution_intent(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionDispatchResponse:
    worker = await build_execution_worker(session)
    intent = await worker.dispatch_next(session)
    if intent is None:
        return ExecutionDispatchResponse(dispatched=False, intent=None, detail="no approved intents available")
    await session.commit()
    return ExecutionDispatchResponse(
        dispatched=True,
        intent=intent_queue_service.to_read(intent),
        detail="approved intent dispatched using runtime-selected adapter",
    )


@router.post("/worker/fail-stale", response_model=ExecutionTimeoutSweepResponse)
async def fail_stale_execution_intents(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionTimeoutSweepResponse:
    worker = await build_execution_worker(session)
    intents = await worker.fail_stale_dispatches(session)
    await session.commit()
    return ExecutionTimeoutSweepResponse(
        timed_out_count=len(intents),
        intents=[intent_queue_service.to_read(intent) for intent in intents],
    )
