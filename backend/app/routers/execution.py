import csv
import io
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.db import AsyncSessionLocal
from app.deps import get_current_user
from app.models import ExecutionIntent, ExecutionVenueEvent, User
from app.models import SpotAccountBalance, SpotExecutionFill, SpotExecutionFillLotClose, SpotPositionLot, SpotSymbolPosition
from app.routers.risk import resolve_live_spot_exposure
from app.schemas.execution import (
    SpotExecutionChainLotCloseRead,
    SpotExecutionChainLotCloseResponse,
    SpotExecutionChainLotCloseSummaryRead,
    BybitExecutionPreviewResponse,
    BybitUserStreamStatusResponse,
    ExecutionIntentCancelRequest,
    ExecutionDispatchResponse,
    ExecutionIntentLineageOutcomeRead,
    ExecutionIntentOutcomeRead,
    ExecutionIntentRead,
    ExecutionIntentReplaceRequest,
    ExecutionIntentReplaceResponse,
    ExecutionOrderReconcileRequest,
    ExecutionReconcileRequest,
    ExecutionIntentStatusUpdateRequest,
    ExecutionIntentSubmitRequest,
    ExecutionIntentSubmitResponse,
    ExecutionTimeoutSweepResponse,
    ExecutionVenueEventIngestRequest,
    ExecutionVenueEventIngestResponse,
    ExecutionVenueEventRead,
    SpotAccountBalanceRead,
    SpotExecutionFillChainRead,
    SpotExecutionFillLotCloseRead,
    SpotExecutionFillRead,
    SpotExecutionFillSummaryRead,
    SpotSymbolPositionRead,
    VenueEventState,
    VenueStatusBucket,
)
from app.schemas.risk import SignalRiskEvaluateResponse
from services.execution.adapter import (
    BybitAuthenticatedExecutionTransport,
    BybitExecutionAdapter,
    PaperExecutionAdapter,
    StubBybitExecutionTransport,
)
from services.execution.account_state import SpotAccountStateService
from services.execution.bybit_runtime import ensure_bybit_runtime_ready, resolve_bybit_execution_runtime
from services.execution.fill_analytics import (
    IntentLineageOutcomeSummary,
    parse_order_chain_key,
    summarize_chain_lot_closes,
    summarize_fill_chains,
    summarize_fill_quality,
    summarize_intent_lineage_outcomes,
    summarize_intent_outcomes,
    summarize_lot_hold_quality,
    summarize_strategy_quality,
    summarize_strategy_lot_hold_quality,
)
from services.execution.intent_queue import ExecutionIntentQueueService
from services.execution.bybit_user_stream import BybitUserStreamService
from services.execution.worker import ExecutionWorkerService
from services.risk.capital_profile import CapitalProfileManager
from services.risk.signal_gate import SignalRiskGate, SignalRiskInput

router = APIRouter(prefix="/execution", tags=["execution"])
intent_queue_service = ExecutionIntentQueueService()
user_stream_service = BybitUserStreamService(
    session_factory=AsyncSessionLocal,
    queue_service=intent_queue_service,
)
account_state_service = SpotAccountStateService()


def compute_hold_seconds(opened_at: datetime | None, closed_at: datetime) -> Decimal | None:
    if opened_at is None:
        return None
    return Decimal(str(max((closed_at - opened_at).total_seconds(), 0)))


def filter_fill_rows(
    fills: list[SpotExecutionFill],
    *,
    strategy: str | None,
    pnl_filter: str | None,
) -> list[SpotExecutionFill]:
    filtered = fills
    if strategy is not None:
        filtered = [fill for fill in filtered if (fill.source_strategy or "unattributed") == strategy]
    if pnl_filter == "winning":
        filtered = [fill for fill in filtered if fill.realized_pnl_usd > 0]
    elif pnl_filter == "losing":
        filtered = [fill for fill in filtered if fill.realized_pnl_usd < 0]
    elif pnl_filter == "flat":
        filtered = [fill for fill in filtered if fill.realized_pnl_usd == 0]
    return filtered


def filter_lineage_rows(
    lineages: list[IntentLineageOutcomeSummary],
    *,
    root_intent_id: int | None,
    latest_intent_id: int | None,
    min_lineage_size: int,
    flagged_only: bool,
    min_slippage_bps: Decimal | None,
    underfilled_only: bool,
) -> list[IntentLineageOutcomeSummary]:
    filtered = [lineage for lineage in lineages if lineage.lineage_size >= min_lineage_size]
    if root_intent_id is not None:
        filtered = [lineage for lineage in filtered if lineage.root_intent_id == root_intent_id]
    if latest_intent_id is not None:
        filtered = [lineage for lineage in filtered if lineage.latest_intent_id == latest_intent_id]
    if flagged_only:
        filtered = [
            lineage
            for lineage in filtered
            if (lineage.slippage_bps is not None and lineage.slippage_bps > Decimal("5"))
            or lineage.fill_ratio < Decimal("0.9")
        ]
    if min_slippage_bps is not None:
        filtered = [
            lineage
            for lineage in filtered
            if lineage.slippage_bps is not None and lineage.slippage_bps >= min_slippage_bps
        ]
    if underfilled_only:
        filtered = [lineage for lineage in filtered if lineage.fill_ratio < Decimal("0.9")]
    return filtered


def filter_venue_event_rows(
    events: list[ExecutionVenueEvent],
    *,
    venue: str | None,
    symbol: str | None,
    query: str | None,
    reconcile_state: VenueEventState | None,
    status_bucket: VenueStatusBucket | None,
    retryable_only: bool,
    severity: str | None,
    suggested_action: str | None,
    queue_service: ExecutionIntentQueueService,
) -> list[ExecutionVenueEvent]:
    filtered = events
    if venue is not None:
        filtered = [event for event in filtered if event.venue == venue]
    if symbol is not None:
        filtered = [event for event in filtered if event.symbol == symbol]
    if reconcile_state is not None:
        filtered = [event for event in filtered if event.reconcile_state == reconcile_state]
    if status_bucket is not None:
        filtered = [
            event
            for event in filtered
            if queue_service.classify_venue_status(event.venue_status) == status_bucket
        ]
    if retryable_only:
        filtered = [
            event
            for event in filtered
            if queue_service.to_venue_event_read(event).retryable
        ]
    if severity is not None:
        filtered = [
            event
            for event in filtered
            if queue_service.to_venue_event_read(event).severity == severity
        ]
    if suggested_action is not None:
        filtered = [
            event
            for event in filtered
            if queue_service.to_venue_event_read(event).suggested_action == suggested_action
        ]
    if query is not None:
        needle = query.strip().lower()
        if needle:
            filtered = [
                event
                for event in filtered
                if any(
                    needle in value
                    for value in [
                        (event.symbol or "").lower(),
                        (event.client_order_id or "").lower(),
                        (event.venue_order_id or "").lower(),
                        (event.event_type or "").lower(),
                        (event.venue_status or "").lower(),
                        str(event.payload.get("retMsg", "")).lower()
                        if isinstance(event.payload, dict)
                        else "",
                        str(event.payload.get("retCode", "")).lower()
                        if isinstance(event.payload, dict)
                        else "",
                    ]
                )
            ]
    return filtered


def csv_response(filename: str, headers: list[str], rows: list[list[object]]) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    payload = io.BytesIO(buffer.getvalue().encode("utf-8"))
    return StreamingResponse(
        payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def venue_events_csv_rows(
    events: list[ExecutionVenueEvent],
    queue_service: ExecutionIntentQueueService,
) -> list[list[object]]:
    rows: list[list[object]] = []
    for event in events:
        event_read = queue_service.to_venue_event_read(event)
        rows.append(
            [
                event_read.id,
                event_read.created_at.isoformat(),
                event_read.venue,
                event_read.event_type,
                event_read.venue_status,
                event_read.status_bucket,
                event_read.reconcile_state,
                event_read.symbol,
                event_read.client_order_id,
                event_read.venue_order_id,
                event_read.ret_code,
                event_read.ret_msg,
                event_read.incident_type,
                event_read.severity,
                event_read.retryable,
                event_read.suggested_action,
            ]
        )
    return rows


async def evaluate_signal_risk(
    payload: ExecutionIntentSubmitRequest,
    session: AsyncSession,
) -> SignalRiskEvaluateResponse:
    settings = get_settings()
    capital_profile = CapitalProfileManager(settings.capital_profiles_path).evaluate(
        payload.signal_risk.current_equity
    )
    live_open_positions, live_total_exposure = await resolve_live_spot_exposure(session)
    current_open_positions = (
        payload.signal_risk.current_open_positions
        if payload.signal_risk.current_open_positions is not None
        else live_open_positions
    )
    current_total_exposure_notional = (
        payload.signal_risk.current_total_exposure_notional
        if payload.signal_risk.current_total_exposure_notional is not None
        else live_total_exposure
    )
    decision = SignalRiskGate().evaluate(
        SignalRiskInput(
            signal=payload.signal_risk.signal,
            current_equity=payload.signal_risk.current_equity,
            entry_price=payload.signal_risk.entry_price,
            proposed_notional=payload.signal_risk.proposed_notional,
            current_open_positions=current_open_positions,
            current_total_exposure_notional=current_total_exposure_notional,
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
        evaluated_open_positions=decision.evaluated_open_positions,
        evaluated_total_exposure_notional=decision.evaluated_total_exposure_notional,
    )


async def build_execution_worker(session: AsyncSession) -> ExecutionWorkerService:
    settings = get_settings()
    if settings.mode in {"live_micro", "live_scaled"}:
        runtime = await resolve_bybit_execution_runtime(session)
        if runtime.live_transport_enabled:
            runtime = await ensure_bybit_runtime_ready(session, runtime)
            adapter = BybitExecutionAdapter(
                transport=BybitAuthenticatedExecutionTransport(
                    api_key=runtime.api_key,
                    api_secret=runtime.api_secret,
                    base_url=runtime.base_url,
                )
            )
        else:
            adapter = BybitExecutionAdapter(transport=StubBybitExecutionTransport())
        return ExecutionWorkerService(intent_queue_service, adapter=adapter)
    return ExecutionWorkerService(intent_queue_service, adapter=PaperExecutionAdapter())


@router.post("/intents/submit", response_model=ExecutionIntentSubmitResponse)
async def submit_execution_intent(
    payload: ExecutionIntentSubmitRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionIntentSubmitResponse:
    risk = await evaluate_signal_risk(payload, session)
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


@router.post("/intents/{intent_id}/replace", response_model=ExecutionIntentReplaceResponse)
async def replace_execution_intent(
    intent_id: int,
    payload: ExecutionIntentReplaceRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionIntentReplaceResponse:
    intent = await session.get(ExecutionIntent, intent_id)
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execution intent not found")
    if intent.status not in {"queued", "approved"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"replacement requires queued or approved status, got {intent.status}",
        )
    if payload.signal_risk.signal.symbol.upper() != intent.symbol:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="replacement symbol must match")
    if payload.signal_risk.signal.side != intent.side:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="replacement side must match")
    if intent.replaced_by_intent_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="execution intent already replaced")

    risk = await evaluate_signal_risk(
        ExecutionIntentSubmitRequest(signal_risk=payload.signal_risk, notes=payload.notes),
        session,
    )
    if not risk.allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "replacement risk evaluation rejected", "reasons": risk.reasons},
        )

    cancel_reason = payload.cancel_reason or "replaced by operator"
    cancelled = await intent_queue_service.update_status(
        session,
        intent=intent,
        status="cancelled",
        notes=cancel_reason,
        execution_payload={
            "status": "cancelled",
            "source": "replacement",
            "cancel_reason": cancel_reason,
            "replaced_at": datetime.now(tz=timezone.utc).isoformat(),
        },
    )
    replacement = await intent_queue_service.enqueue(
        session,
        user=user,
        risk_request=payload.signal_risk,
        risk_response=risk,
        notes=payload.notes,
        parent_intent_id=int(cancelled.id) if cancelled.id is not None else None,
    )
    await intent_queue_service.link_replacement(
        session,
        intent=cancelled,
        replacement_intent=replacement,
    )
    await session.commit()
    return ExecutionIntentReplaceResponse(
        risk=risk,
        cancelled_intent=intent_queue_service.to_read(cancelled),
        replacement_intent=intent_queue_service.to_read(replacement),
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


@router.get("/venues/bybit/intents/{intent_id}/preview-order", response_model=BybitExecutionPreviewResponse)
async def preview_bybit_order_request(
    intent_id: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BybitExecutionPreviewResponse:
    intent = await session.get(ExecutionIntent, intent_id)
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execution intent not found")
    try:
        runtime = await resolve_bybit_execution_runtime(session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if runtime.live_transport_enabled:
        try:
            runtime = await ensure_bybit_runtime_ready(session, runtime)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    adapter = BybitExecutionAdapter()
    request = adapter.build_order_request(intent)
    unsigned_payload = request.payload()
    return BybitExecutionPreviewResponse(
        symbol=intent.symbol,
        side=intent.side,
        base_url=runtime.base_url,
        testnet=runtime.testnet,
        live_transport_enabled=runtime.live_transport_enabled,
        transport_mode="authenticated" if runtime.live_transport_enabled else "stub",
        client_order_id=request.order_link_id,
        unsigned_payload=unsigned_payload,
        signed_payload_keys=sorted(unsigned_payload.keys()),
    )


@router.get("/venues/bybit/user-stream/status", response_model=BybitUserStreamStatusResponse)
async def bybit_user_stream_status(_: User = Depends(get_current_user)) -> BybitUserStreamStatusResponse:
    status_payload = user_stream_service.status()
    return BybitUserStreamStatusResponse(
        running=status_payload.running,
        subscribed=status_payload.subscribed,
        reconnect_attempts=status_payload.reconnect_attempts,
        messages_processed=status_payload.messages_processed,
        subscription_id=status_payload.subscription_id,
        last_event_type=status_payload.last_event_type,
        last_message_at=status_payload.last_message_at,
        last_error=status_payload.last_error,
    )


@router.post("/venues/bybit/user-stream/start", response_model=BybitUserStreamStatusResponse)
async def start_bybit_user_stream(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BybitUserStreamStatusResponse:
    try:
        runtime = await resolve_bybit_execution_runtime(session)
        await ensure_bybit_runtime_ready(session, runtime)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    status_payload = await user_stream_service.start()
    return BybitUserStreamStatusResponse(
        running=status_payload.running,
        subscribed=status_payload.subscribed,
        reconnect_attempts=status_payload.reconnect_attempts,
        messages_processed=status_payload.messages_processed,
        subscription_id=status_payload.subscription_id,
        last_event_type=status_payload.last_event_type,
        last_message_at=status_payload.last_message_at,
        last_error=status_payload.last_error,
    )


@router.post("/venues/bybit/user-stream/stop", response_model=BybitUserStreamStatusResponse)
async def stop_bybit_user_stream(_: User = Depends(get_current_user)) -> BybitUserStreamStatusResponse:
    status_payload = await user_stream_service.stop()
    return BybitUserStreamStatusResponse(
        running=status_payload.running,
        subscribed=status_payload.subscribed,
        reconnect_attempts=status_payload.reconnect_attempts,
        messages_processed=status_payload.messages_processed,
        subscription_id=status_payload.subscription_id,
        last_event_type=status_payload.last_event_type,
        last_message_at=status_payload.last_message_at,
        last_error=status_payload.last_error,
    )


@router.get("/account/balances", response_model=list[SpotAccountBalanceRead])
async def list_spot_account_balances(
    limit: int = Query(default=25, ge=1, le=200),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SpotAccountBalanceRead]:
    balances = list(
        (
            await session.scalars(
                select(SpotAccountBalance)
                .order_by(SpotAccountBalance.total_value_usd.desc().nullslast(), SpotAccountBalance.asset.asc())
                .limit(limit)
            )
        ).all()
    )
    return [
        SpotAccountBalanceRead(
            asset=balance.asset,
            free=balance.free,
            locked=balance.locked,
            total=balance.total,
            total_value_usd=balance.total_value_usd,
            last_delta=balance.last_delta,
            updated_at=balance.updated_at,
            source_event=balance.source_event,
        )
        for balance in balances
    ]


@router.get("/account/positions", response_model=list[SpotSymbolPositionRead])
async def list_spot_symbol_positions(
    limit: int = Query(default=25, ge=1, le=200),
    refresh_marks: bool = Query(default=True),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SpotSymbolPositionRead]:
    positions = list(
        (
            await session.scalars(
                select(SpotSymbolPosition)
                .order_by(SpotSymbolPosition.quote_exposure_usd.desc().nullslast(), SpotSymbolPosition.symbol.asc())
                .limit(limit)
            )
        ).all()
    )
    if refresh_marks:
        await account_state_service.refresh_all_position_marks(session, positions)
        await session.commit()
    return [
        SpotSymbolPositionRead(
            symbol=position.symbol,
            base_asset=position.base_asset,
            quote_asset=position.quote_asset,
            net_quantity=position.net_quantity,
            average_entry_price=position.average_entry_price,
            last_mark_price=position.last_mark_price,
            quote_exposure_usd=position.quote_exposure_usd,
            market_value_usd=position.market_value_usd,
            realized_notional=position.realized_notional,
            realized_pnl_usd=position.realized_pnl_usd,
            unrealized_pnl_usd=position.unrealized_pnl_usd,
            updated_at=position.updated_at,
            source_event=position.source_event,
        )
        for position in positions
    ]


@router.get("/account/fills", response_model=list[SpotExecutionFillRead])
async def list_spot_execution_fills(
    symbol: str | None = Query(default=None, max_length=32),
    strategy: str | None = Query(default=None, max_length=64),
    execution_intent_id: int | None = Query(default=None, ge=1),
    pnl_filter: str | None = Query(default=None, pattern="^(winning|losing|flat)$"),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0, le=10000),
    limit: int = Query(default=50, ge=1, le=500),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SpotExecutionFillRead]:
    query = select(SpotExecutionFill).order_by(SpotExecutionFill.filled_at.desc()).offset(offset).limit(limit)
    if symbol is not None:
        query = query.where(SpotExecutionFill.symbol == symbol.upper())
    if execution_intent_id is not None:
        query = query.where(SpotExecutionFill.execution_intent_id == execution_intent_id)
    if start_at is not None:
        query = query.where(SpotExecutionFill.filled_at >= start_at)
    if end_at is not None:
        query = query.where(SpotExecutionFill.filled_at <= end_at)
    fills = filter_fill_rows(
        list((await session.scalars(query)).all()),
        strategy=strategy,
        pnl_filter=pnl_filter,
    )
    return [
        SpotExecutionFillRead(
            id=int(fill.id),
            filled_at=fill.filled_at,
            symbol=fill.symbol,
            side=fill.side,
            execution_intent_id=int(fill.execution_intent_id) if fill.execution_intent_id is not None else None,
            source_strategy=fill.source_strategy,
            client_order_id=fill.client_order_id,
            venue_order_id=fill.venue_order_id,
            trade_id=fill.trade_id,
            quantity=fill.quantity,
            quote_quantity=fill.quote_quantity,
            price=fill.price,
            realized_pnl_usd=fill.realized_pnl_usd,
            post_fill_net_quantity=fill.post_fill_net_quantity,
            post_fill_average_entry_price=fill.post_fill_average_entry_price,
            source_event=fill.source_event,
        )
        for fill in fills
    ]


@router.get("/account/fills/{fill_id}/lot-closes", response_model=list[SpotExecutionFillLotCloseRead])
async def list_spot_execution_fill_lot_closes(
    fill_id: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SpotExecutionFillLotCloseRead]:
    lot_closes = list(
        (
            await session.scalars(
                select(SpotExecutionFillLotClose)
                .where(SpotExecutionFillLotClose.execution_fill_id == fill_id)
                .order_by(SpotExecutionFillLotClose.closed_at.asc(), SpotExecutionFillLotClose.id.asc())
            )
        ).all()
    )
    lot_by_id = {
        int(lot.id): lot
        for lot in (
            await session.scalars(
                select(SpotPositionLot).where(
                    SpotPositionLot.id.in_([int(item.position_lot_id) for item in lot_closes])
                )
            )
        ).all()
    } if lot_closes else {}
    rows: list[SpotExecutionFillLotCloseRead] = []
    for item in lot_closes:
        lot = lot_by_id.get(int(item.position_lot_id))
        lot_opened_at = lot.opened_at if lot is not None else None
        rows.append(
            SpotExecutionFillLotCloseRead(
                id=int(item.id),
                execution_fill_id=int(item.execution_fill_id),
                position_lot_id=int(item.position_lot_id),
                symbol=item.symbol,
                closed_quantity=item.closed_quantity,
                lot_entry_price=item.lot_entry_price,
                fill_exit_price=item.fill_exit_price,
                realized_pnl_usd=item.realized_pnl_usd,
                lot_opened_at=lot_opened_at,
                hold_seconds=compute_hold_seconds(lot_opened_at, item.closed_at),
                closed_at=item.closed_at,
            )
        )
    return rows


@router.get("/account/fills/chains/{chain_key}/lot-closes", response_model=SpotExecutionChainLotCloseResponse)
async def summarize_spot_execution_chain_lot_closes(
    chain_key: str,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SpotExecutionChainLotCloseResponse:
    parsed_chain = parse_order_chain_key(chain_key)
    if parsed_chain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown chain key")
    chain_type, chain_value = parsed_chain
    fill_query = select(SpotExecutionFill).order_by(SpotExecutionFill.filled_at.asc(), SpotExecutionFill.id.asc())
    if chain_type == "client":
        fill_query = fill_query.where(SpotExecutionFill.client_order_id == chain_value)
    elif chain_type == "venue":
        fill_query = fill_query.where(SpotExecutionFill.venue_order_id == chain_value)
    else:
        fill_query = fill_query.where(SpotExecutionFill.id == chain_value)
    fills = list((await session.scalars(fill_query)).all())
    if not fills:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="chain not found")

    fill_ids = [int(fill.id) for fill in fills]
    lot_close_rows = list(
        (
            await session.scalars(
                select(SpotExecutionFillLotClose)
                .where(SpotExecutionFillLotClose.execution_fill_id.in_(fill_ids))
                .order_by(SpotExecutionFillLotClose.closed_at.asc(), SpotExecutionFillLotClose.id.asc())
            )
        ).all()
    )
    fill_by_id = {int(fill.id): fill for fill in fills}
    lot_by_id = {
        int(lot.id): lot
        for lot in (
            await session.scalars(
                select(SpotPositionLot).where(
                    SpotPositionLot.id.in_([int(item.position_lot_id) for item in lot_close_rows])
                )
            )
        ).all()
    } if lot_close_rows else {}
    summary = summarize_chain_lot_closes(
        chain_key,
        fills,
        lot_close_rows,
        {lot_id: lot.opened_at for lot_id, lot in lot_by_id.items()},
    )
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="chain not found")
    return SpotExecutionChainLotCloseResponse(
        summary=SpotExecutionChainLotCloseSummaryRead(
            chain_key=summary.chain_key,
            symbol=summary.symbol,
            fills_count=summary.fills_count,
            lot_slices_count=summary.lot_slices_count,
            lots_count=summary.lots_count,
            total_closed_quantity=summary.total_closed_quantity,
            total_realized_pnl_usd=summary.total_realized_pnl_usd,
            weighted_average_entry_price=summary.weighted_average_entry_price,
            weighted_average_exit_price=summary.weighted_average_exit_price,
            average_hold_seconds=summary.average_hold_seconds,
            max_hold_seconds=summary.max_hold_seconds,
            opened_at=summary.opened_at,
            closed_at=summary.closed_at,
        ),
        rows=[
            SpotExecutionChainLotCloseRead(
                id=int(item.id),
                execution_fill_id=int(item.execution_fill_id),
                position_lot_id=int(item.position_lot_id),
                symbol=item.symbol,
                closed_quantity=item.closed_quantity,
                lot_entry_price=item.lot_entry_price,
                fill_exit_price=item.fill_exit_price,
                realized_pnl_usd=item.realized_pnl_usd,
                lot_opened_at=(lot_by_id[int(item.position_lot_id)].opened_at if int(item.position_lot_id) in lot_by_id else None),
                hold_seconds=compute_hold_seconds(
                    (lot_by_id[int(item.position_lot_id)].opened_at if int(item.position_lot_id) in lot_by_id else None),
                    item.closed_at,
                ),
                closed_at=item.closed_at,
                fill_client_order_id=fill_by_id[int(item.execution_fill_id)].client_order_id,
                fill_venue_order_id=fill_by_id[int(item.execution_fill_id)].venue_order_id,
                fill_source_strategy=fill_by_id[int(item.execution_fill_id)].source_strategy,
            )
            for item in lot_close_rows
        ],
    )


@router.get("/account/fills/export")
async def export_spot_execution_fills_csv(
    symbol: str | None = Query(default=None, max_length=32),
    strategy: str | None = Query(default=None, max_length=64),
    execution_intent_id: int | None = Query(default=None, ge=1),
    pnl_filter: str | None = Query(default=None, pattern="^(winning|losing|flat)$"),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0, le=10000),
    limit: int = Query(default=500, ge=1, le=5000),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    query = select(SpotExecutionFill).order_by(SpotExecutionFill.filled_at.desc()).offset(offset).limit(limit)
    if symbol is not None:
        query = query.where(SpotExecutionFill.symbol == symbol.upper())
    if execution_intent_id is not None:
        query = query.where(SpotExecutionFill.execution_intent_id == execution_intent_id)
    if start_at is not None:
        query = query.where(SpotExecutionFill.filled_at >= start_at)
    if end_at is not None:
        query = query.where(SpotExecutionFill.filled_at <= end_at)
    fills = filter_fill_rows(
        list((await session.scalars(query)).all()),
        strategy=strategy,
        pnl_filter=pnl_filter,
    )
    return csv_response(
        "execution-fills.csv",
        [
            "filled_at",
            "symbol",
            "side",
            "execution_intent_id",
            "source_strategy",
            "client_order_id",
            "venue_order_id",
            "trade_id",
            "quantity",
            "quote_quantity",
            "price",
            "realized_pnl_usd",
            "post_fill_net_quantity",
            "post_fill_average_entry_price",
            "source_event",
        ],
        [
            [
                fill.filled_at.isoformat(),
                fill.symbol,
                fill.side,
                fill.execution_intent_id,
                fill.source_strategy,
                fill.client_order_id,
                fill.venue_order_id,
                fill.trade_id,
                fill.quantity,
                fill.quote_quantity,
                fill.price,
                fill.realized_pnl_usd,
                fill.post_fill_net_quantity,
                fill.post_fill_average_entry_price,
                fill.source_event,
            ]
            for fill in fills
        ],
    )


@router.get("/account/fills/summary", response_model=SpotExecutionFillSummaryRead)
async def summarize_spot_execution_fills(
    symbol: str | None = Query(default=None, max_length=32),
    strategy: str | None = Query(default=None, max_length=64),
    execution_intent_id: int | None = Query(default=None, ge=1),
    pnl_filter: str | None = Query(default=None, pattern="^(winning|losing|flat)$"),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    limit: int = Query(default=250, ge=1, le=2000),
    recent_chains_limit: int = Query(default=20, ge=1, le=100),
    recent_chains_offset: int = Query(default=0, ge=0, le=1000),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SpotExecutionFillSummaryRead:
    query = select(SpotExecutionFill).order_by(SpotExecutionFill.filled_at.desc()).limit(limit)
    if symbol is not None:
        query = query.where(SpotExecutionFill.symbol == symbol.upper())
    if execution_intent_id is not None:
        query = query.where(SpotExecutionFill.execution_intent_id == execution_intent_id)
    if start_at is not None:
        query = query.where(SpotExecutionFill.filled_at >= start_at)
    if end_at is not None:
        query = query.where(SpotExecutionFill.filled_at <= end_at)
    fills = filter_fill_rows(
        list((await session.scalars(query)).all()),
        strategy=strategy,
        pnl_filter=pnl_filter,
    )
    fill_ids = [int(fill.id) for fill in fills]
    lot_close_rows = list(
        (
            await session.scalars(
                select(SpotExecutionFillLotClose)
                .where(SpotExecutionFillLotClose.execution_fill_id.in_(fill_ids))
                .order_by(SpotExecutionFillLotClose.closed_at.asc(), SpotExecutionFillLotClose.id.asc())
            )
        ).all()
    ) if fill_ids else []
    lot_by_id = {
        int(lot.id): lot
        for lot in (
            await session.scalars(
                select(SpotPositionLot).where(
                    SpotPositionLot.id.in_([int(item.position_lot_id) for item in lot_close_rows])
                )
            )
        ).all()
    } if lot_close_rows else {}
    summary = summarize_fill_quality(fills)
    chains = summarize_fill_chains(fills)[recent_chains_offset : recent_chains_offset + recent_chains_limit]
    strategy_breakdown = summarize_strategy_quality(fills)
    hold_summary = summarize_lot_hold_quality(
        lot_close_rows,
        strategy_by_fill_id={int(fill.id): fill.source_strategy for fill in fills},
        lot_opened_at={lot_id: lot.opened_at for lot_id, lot in lot_by_id.items()},
    )
    strategy_hold_breakdown = {
        item.source_strategy: item
        for item in summarize_strategy_lot_hold_quality(
            lot_close_rows,
            strategy_by_fill_id={int(fill.id): fill.source_strategy for fill in fills},
            lot_opened_at={lot_id: lot.opened_at for lot_id, lot in lot_by_id.items()},
        )
    }
    return SpotExecutionFillSummaryRead(
        fills_count=summary.fills_count,
        chains_count=summary.chains_count,
        traded_symbols_count=summary.traded_symbols_count,
        gross_notional_usd=summary.gross_notional_usd,
        gross_realized_pnl_usd=summary.gross_realized_pnl_usd,
        winning_fills_count=summary.winning_fills_count,
        losing_fills_count=summary.losing_fills_count,
        flat_fills_count=summary.flat_fills_count,
        win_rate=summary.win_rate,
        average_fill_notional_usd=summary.average_fill_notional_usd,
        average_realized_pnl_per_fill_usd=summary.average_realized_pnl_per_fill_usd,
        gross_adverse_slippage_cost_usd=summary.gross_adverse_slippage_cost_usd,
        average_adverse_slippage_bps=summary.average_adverse_slippage_bps,
        lot_closes_count=hold_summary.lot_closes_count,
        average_hold_seconds=hold_summary.average_hold_seconds,
        max_hold_seconds=hold_summary.max_hold_seconds,
        average_realized_pnl_per_lot_close_usd=hold_summary.average_realized_pnl_per_lot_close_usd,
        short_hold_realized_pnl_usd=hold_summary.short_hold_realized_pnl_usd,
        long_hold_realized_pnl_usd=hold_summary.long_hold_realized_pnl_usd,
        strategy_breakdown=[
            {
                "source_strategy": item.source_strategy,
                "fills_count": item.fills_count,
                "chains_count": item.chains_count,
                "gross_notional_usd": item.gross_notional_usd,
                "gross_realized_pnl_usd": item.gross_realized_pnl_usd,
                "win_rate": item.win_rate,
                "gross_adverse_slippage_cost_usd": item.gross_adverse_slippage_cost_usd,
                "average_adverse_slippage_bps": item.average_adverse_slippage_bps,
                "gross_underfill_notional_usd": item.gross_underfill_notional_usd,
                "lot_closes_count": (
                    strategy_hold_breakdown[item.source_strategy].lot_closes_count
                    if item.source_strategy in strategy_hold_breakdown
                    else 0
                ),
                "average_hold_seconds": (
                    strategy_hold_breakdown[item.source_strategy].average_hold_seconds
                    if item.source_strategy in strategy_hold_breakdown
                    else None
                ),
                "max_hold_seconds": (
                    strategy_hold_breakdown[item.source_strategy].max_hold_seconds
                    if item.source_strategy in strategy_hold_breakdown
                    else None
                ),
                "average_realized_pnl_per_lot_close_usd": (
                    strategy_hold_breakdown[item.source_strategy].average_realized_pnl_per_lot_close_usd
                    if item.source_strategy in strategy_hold_breakdown
                    else Decimal("0")
                ),
                "short_hold_realized_pnl_usd": (
                    strategy_hold_breakdown[item.source_strategy].short_hold_realized_pnl_usd
                    if item.source_strategy in strategy_hold_breakdown
                    else Decimal("0")
                ),
                "long_hold_realized_pnl_usd": (
                    strategy_hold_breakdown[item.source_strategy].long_hold_realized_pnl_usd
                    if item.source_strategy in strategy_hold_breakdown
                    else Decimal("0")
                ),
            }
            for item in strategy_breakdown
        ],
        recent_chains=[
            SpotExecutionFillChainRead(
                chain_key=chain.chain_key,
                symbol=chain.symbol,
                side=chain.side,
                execution_intent_id=chain.execution_intent_id,
                source_strategy=chain.source_strategy,
                client_order_id=chain.client_order_id,
                venue_order_id=chain.venue_order_id,
                fills_count=chain.fills_count,
                opened_at=chain.opened_at,
                closed_at=chain.closed_at,
                total_quantity=chain.total_quantity,
                total_quote_quantity=chain.total_quote_quantity,
                average_price=chain.average_price,
                realized_pnl_usd=chain.realized_pnl_usd,
                ending_net_quantity=chain.ending_net_quantity,
                ending_average_entry_price=chain.ending_average_entry_price,
            )
            for chain in chains
        ],
    )


@router.get("/account/fills/chains/export")
async def export_spot_execution_fill_chains_csv(
    symbol: str | None = Query(default=None, max_length=32),
    strategy: str | None = Query(default=None, max_length=64),
    execution_intent_id: int | None = Query(default=None, ge=1),
    pnl_filter: str | None = Query(default=None, pattern="^(winning|losing|flat)$"),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    recent_chains_limit: int = Query(default=100, ge=1, le=1000),
    recent_chains_offset: int = Query(default=0, ge=0, le=5000),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    query = select(SpotExecutionFill).order_by(SpotExecutionFill.filled_at.desc()).limit(limit)
    if symbol is not None:
        query = query.where(SpotExecutionFill.symbol == symbol.upper())
    if execution_intent_id is not None:
        query = query.where(SpotExecutionFill.execution_intent_id == execution_intent_id)
    if start_at is not None:
        query = query.where(SpotExecutionFill.filled_at >= start_at)
    if end_at is not None:
        query = query.where(SpotExecutionFill.filled_at <= end_at)
    fills = filter_fill_rows(
        list((await session.scalars(query)).all()),
        strategy=strategy,
        pnl_filter=pnl_filter,
    )
    chains = summarize_fill_chains(fills)[recent_chains_offset : recent_chains_offset + recent_chains_limit]
    return csv_response(
        "execution-chains.csv",
        [
            "chain_key",
            "symbol",
            "side",
            "execution_intent_id",
            "source_strategy",
            "client_order_id",
            "venue_order_id",
            "fills_count",
            "opened_at",
            "closed_at",
            "total_quantity",
            "total_quote_quantity",
            "average_price",
            "realized_pnl_usd",
            "ending_net_quantity",
            "ending_average_entry_price",
        ],
        [
            [
                chain.chain_key,
                chain.symbol,
                chain.side,
                chain.execution_intent_id,
                chain.source_strategy,
                chain.client_order_id,
                chain.venue_order_id,
                chain.fills_count,
                chain.opened_at.isoformat(),
                chain.closed_at.isoformat(),
                chain.total_quantity,
                chain.total_quote_quantity,
                chain.average_price,
                chain.realized_pnl_usd,
                chain.ending_net_quantity,
                chain.ending_average_entry_price,
            ]
            for chain in chains
        ],
    )


@router.get("/intents/outcomes", response_model=list[ExecutionIntentOutcomeRead])
async def list_execution_intent_outcomes(
    strategy: str | None = Query(default=None, max_length=64),
    status_filter: str | None = Query(default=None, alias="status"),
    execution_intent_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ExecutionIntentOutcomeRead]:
    query = select(ExecutionIntent).order_by(ExecutionIntent.created_at.desc()).limit(limit)
    if strategy is not None:
        query = query.where(ExecutionIntent.source_strategy == strategy)
    if status_filter is not None:
        query = query.where(ExecutionIntent.status == status_filter)
    if execution_intent_id is not None:
        query = query.where(ExecutionIntent.id == execution_intent_id)
    intents = list((await session.scalars(query)).all())
    intent_ids = [int(intent.id) for intent in intents if intent.id is not None]
    fills: list[SpotExecutionFill] = []
    if intent_ids:
        fills = list(
            (
                await session.scalars(
                    select(SpotExecutionFill)
                    .where(SpotExecutionFill.execution_intent_id.in_(intent_ids))
                    .order_by(SpotExecutionFill.filled_at.desc())
                )
            ).all()
        )

    return [
        ExecutionIntentOutcomeRead(
            execution_intent_id=item.execution_intent_id,
            symbol=item.symbol,
            side=item.side,
            source_strategy=item.source_strategy,
            intent_status=item.intent_status,
            requested_notional=item.requested_notional,
            approved_notional=item.approved_notional,
            entry_price=item.entry_price,
            created_at=item.created_at,
            dispatched_at=item.dispatched_at,
            executed_at=item.executed_at,
            fills_count=item.fills_count,
            filled_quantity=item.filled_quantity,
            filled_quote_quantity=item.filled_quote_quantity,
            average_fill_price=item.average_fill_price,
            realized_pnl_usd=item.realized_pnl_usd,
            fill_ratio=item.fill_ratio,
            slippage_bps=item.slippage_bps,
            adverse_slippage_bps=item.adverse_slippage_bps,
            slippage_cost_usd=item.slippage_cost_usd,
            underfill_notional_usd=item.underfill_notional_usd,
            last_fill_at=item.last_fill_at,
        )
        for item in summarize_intent_outcomes(intents, fills)
    ]


@router.get("/intents/lineages/outcomes", response_model=list[ExecutionIntentLineageOutcomeRead])
async def list_execution_intent_lineage_outcomes(
    strategy: str | None = Query(default=None, max_length=64),
    status_filter: str | None = Query(default=None, alias="status"),
    root_intent_id: int | None = Query(default=None, ge=1),
    latest_intent_id: int | None = Query(default=None, ge=1),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    min_lineage_size: int = Query(default=1, ge=1, le=50),
    flagged_only: bool = Query(default=False),
    min_slippage_bps: Decimal | None = Query(default=None, ge=0),
    underfilled_only: bool = Query(default=False),
    offset: int = Query(default=0, ge=0, le=5000),
    limit: int = Query(default=100, ge=1, le=1000),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ExecutionIntentLineageOutcomeRead]:
    query = select(ExecutionIntent).order_by(ExecutionIntent.created_at.desc()).offset(offset).limit(limit)
    if strategy is not None:
        query = query.where(ExecutionIntent.source_strategy == strategy)
    if status_filter is not None:
        query = query.where(ExecutionIntent.status == status_filter)
    if start_at is not None:
        query = query.where(ExecutionIntent.created_at >= start_at)
    if end_at is not None:
        query = query.where(ExecutionIntent.created_at <= end_at)
    intents = list((await session.scalars(query)).all())
    intent_ids = [int(intent.id) for intent in intents if intent.id is not None]
    fills: list[SpotExecutionFill] = []
    if intent_ids:
        fills = list(
            (
                await session.scalars(
                    select(SpotExecutionFill)
                    .where(SpotExecutionFill.execution_intent_id.in_(intent_ids))
                    .order_by(SpotExecutionFill.filled_at.desc())
                )
            ).all()
        )
    fill_ids = [int(fill.id) for fill in fills if fill.id is not None]
    lot_closes = list(
        (
            await session.scalars(
                select(SpotExecutionFillLotClose)
                .where(SpotExecutionFillLotClose.execution_fill_id.in_(fill_ids))
                .order_by(SpotExecutionFillLotClose.closed_at.desc(), SpotExecutionFillLotClose.id.desc())
            )
        ).all()
    ) if fill_ids else []
    lot_by_id = {
        int(lot.id): lot
        for lot in (
            await session.scalars(
                select(SpotPositionLot).where(
                    SpotPositionLot.id.in_([int(item.position_lot_id) for item in lot_closes])
                )
            )
        ).all()
    } if lot_closes else {}

    lineages = filter_lineage_rows(
        summarize_intent_lineage_outcomes(
            intents,
            fills,
            lot_closes=lot_closes,
            lot_opened_at={lot_id: lot.opened_at for lot_id, lot in lot_by_id.items()},
        ),
        root_intent_id=root_intent_id,
        latest_intent_id=latest_intent_id,
        min_lineage_size=min_lineage_size,
        flagged_only=flagged_only,
        min_slippage_bps=min_slippage_bps,
        underfilled_only=underfilled_only,
    )
    return [
        ExecutionIntentLineageOutcomeRead(
            root_intent_id=item.root_intent_id,
            latest_intent_id=item.latest_intent_id,
            symbol=item.symbol,
            side=item.side,
            source_strategy=item.source_strategy,
            lineage_size=item.lineage_size,
            lineage_statuses=item.lineage_statuses,
            requested_notional=item.requested_notional,
            approved_notional=item.approved_notional,
            created_at=item.created_at,
            latest_created_at=item.latest_created_at,
            fills_count=item.fills_count,
            filled_quantity=item.filled_quantity,
            filled_quote_quantity=item.filled_quote_quantity,
            average_fill_price=item.average_fill_price,
            realized_pnl_usd=item.realized_pnl_usd,
            fill_ratio=item.fill_ratio,
            slippage_bps=item.slippage_bps,
            adverse_slippage_bps=item.adverse_slippage_bps,
            slippage_cost_usd=item.slippage_cost_usd,
            underfill_notional_usd=item.underfill_notional_usd,
            average_hold_seconds=item.average_hold_seconds,
            max_hold_seconds=item.max_hold_seconds,
            short_hold_realized_pnl_usd=item.short_hold_realized_pnl_usd,
            long_hold_realized_pnl_usd=item.long_hold_realized_pnl_usd,
            last_fill_at=item.last_fill_at,
        )
        for item in lineages
    ]


@router.get("/intents/lineages/outcomes/export")
async def export_execution_intent_lineages_csv(
    strategy: str | None = Query(default=None, max_length=64),
    status_filter: str | None = Query(default=None, alias="status"),
    root_intent_id: int | None = Query(default=None, ge=1),
    latest_intent_id: int | None = Query(default=None, ge=1),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    min_lineage_size: int = Query(default=1, ge=1, le=50),
    flagged_only: bool = Query(default=False),
    min_slippage_bps: Decimal | None = Query(default=None, ge=0),
    underfilled_only: bool = Query(default=False),
    offset: int = Query(default=0, ge=0, le=5000),
    limit: int = Query(default=500, ge=1, le=5000),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    query = select(ExecutionIntent).order_by(ExecutionIntent.created_at.desc()).offset(offset).limit(limit)
    if strategy is not None:
        query = query.where(ExecutionIntent.source_strategy == strategy)
    if status_filter is not None:
        query = query.where(ExecutionIntent.status == status_filter)
    if start_at is not None:
        query = query.where(ExecutionIntent.created_at >= start_at)
    if end_at is not None:
        query = query.where(ExecutionIntent.created_at <= end_at)
    intents = list((await session.scalars(query)).all())
    intent_ids = [int(intent.id) for intent in intents if intent.id is not None]
    fills: list[SpotExecutionFill] = []
    if intent_ids:
        fills = list(
            (
                await session.scalars(
                    select(SpotExecutionFill)
                    .where(SpotExecutionFill.execution_intent_id.in_(intent_ids))
                    .order_by(SpotExecutionFill.filled_at.desc())
                )
            ).all()
        )
    fill_ids = [int(fill.id) for fill in fills if fill.id is not None]
    lot_closes = list(
        (
            await session.scalars(
                select(SpotExecutionFillLotClose)
                .where(SpotExecutionFillLotClose.execution_fill_id.in_(fill_ids))
                .order_by(SpotExecutionFillLotClose.closed_at.desc(), SpotExecutionFillLotClose.id.desc())
            )
        ).all()
    ) if fill_ids else []
    lot_by_id = {
        int(lot.id): lot
        for lot in (
            await session.scalars(
                select(SpotPositionLot).where(
                    SpotPositionLot.id.in_([int(item.position_lot_id) for item in lot_closes])
                )
            )
        ).all()
    } if lot_closes else {}
    lineages = filter_lineage_rows(
        summarize_intent_lineage_outcomes(
            intents,
            fills,
            lot_closes=lot_closes,
            lot_opened_at={lot_id: lot.opened_at for lot_id, lot in lot_by_id.items()},
        ),
        root_intent_id=root_intent_id,
        latest_intent_id=latest_intent_id,
        min_lineage_size=min_lineage_size,
        flagged_only=flagged_only,
        min_slippage_bps=min_slippage_bps,
        underfilled_only=underfilled_only,
    )
    return csv_response(
        "execution-lineages.csv",
        [
            "root_intent_id",
            "latest_intent_id",
            "symbol",
            "side",
            "source_strategy",
            "lineage_size",
            "lineage_statuses",
            "requested_notional",
            "approved_notional",
            "created_at",
            "latest_created_at",
            "fills_count",
            "filled_quantity",
            "filled_quote_quantity",
            "average_fill_price",
            "realized_pnl_usd",
            "fill_ratio",
            "slippage_bps",
            "adverse_slippage_bps",
            "slippage_cost_usd",
            "underfill_notional_usd",
            "average_hold_seconds",
            "max_hold_seconds",
            "short_hold_realized_pnl_usd",
            "long_hold_realized_pnl_usd",
            "last_fill_at",
        ],
        [
            [
                item.root_intent_id,
                item.latest_intent_id,
                item.symbol,
                item.side,
                item.source_strategy,
                item.lineage_size,
                " | ".join(item.lineage_statuses),
                item.requested_notional,
                item.approved_notional,
                item.created_at.isoformat(),
                item.latest_created_at.isoformat(),
                item.fills_count,
                item.filled_quantity,
                item.filled_quote_quantity,
                item.average_fill_price,
                item.realized_pnl_usd,
                item.fill_ratio,
                item.slippage_bps,
                item.adverse_slippage_bps,
                item.slippage_cost_usd,
                item.underfill_notional_usd,
                item.average_hold_seconds,
                item.max_hold_seconds,
                item.short_hold_realized_pnl_usd,
                item.long_hold_realized_pnl_usd,
                item.last_fill_at.isoformat() if item.last_fill_at is not None else None,
            ]
            for item in lineages
        ],
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


@router.post("/intents/{intent_id}/cancel", response_model=ExecutionIntentRead)
async def cancel_execution_intent(
    intent_id: int,
    payload: ExecutionIntentCancelRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExecutionIntentRead:
    intent = await session.get(ExecutionIntent, intent_id)
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execution intent not found")
    worker = await build_execution_worker(session)
    try:
        intent = await worker.request_cancel(
            session,
            intent=intent,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
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


@router.get("/venues/events", response_model=list[ExecutionVenueEventRead])
async def list_execution_venue_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    venue: str | None = Query(default=None, max_length=64),
    symbol: str | None = Query(default=None, max_length=32),
    query: str | None = Query(default=None, max_length=128),
    reconcile_state: VenueEventState | None = Query(default=None),
    status_bucket: VenueStatusBucket | None = Query(default=None),
    retryable_only: bool = Query(default=False),
    severity: str | None = Query(default=None, pattern="^(low|medium|high)$"),
    suggested_action: str | None = Query(default=None, pattern="^(retry_later|reduce_size|refresh_order_state|fix_request|manual_review)$"),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ExecutionVenueEventRead]:
    events = list(
        (
            await session.scalars(
                select(ExecutionVenueEvent)
                .order_by(ExecutionVenueEvent.created_at.desc())
                .limit(limit + offset)
            )
        ).all()
    )
    filtered = filter_venue_event_rows(
        events,
        venue=venue,
        symbol=symbol,
        query=query,
        reconcile_state=reconcile_state,
        status_bucket=status_bucket,
        retryable_only=retryable_only,
        severity=severity,
        suggested_action=suggested_action,
        queue_service=intent_queue_service,
    )
    page = filtered[offset : offset + limit]
    return [intent_queue_service.to_venue_event_read(event) for event in page]


@router.get("/venues/events/export")
async def export_execution_venue_events(
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    venue: str | None = Query(default=None, max_length=64),
    symbol: str | None = Query(default=None, max_length=32),
    query: str | None = Query(default=None, max_length=128),
    reconcile_state: VenueEventState | None = Query(default=None),
    status_bucket: VenueStatusBucket | None = Query(default=None),
    retryable_only: bool = Query(default=False),
    severity: str | None = Query(default=None, pattern="^(low|medium|high)$"),
    suggested_action: str | None = Query(default=None, pattern="^(retry_later|reduce_size|refresh_order_state|fix_request|manual_review)$"),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    events = list(
        (
            await session.scalars(
                select(ExecutionVenueEvent)
                .order_by(ExecutionVenueEvent.created_at.desc())
                .limit(limit + offset)
            )
        ).all()
    )
    filtered = filter_venue_event_rows(
        events,
        venue=venue,
        symbol=symbol,
        query=query,
        reconcile_state=reconcile_state,
        status_bucket=status_bucket,
        retryable_only=retryable_only,
        severity=severity,
        suggested_action=suggested_action,
        queue_service=intent_queue_service,
    )
    page = filtered[offset : offset + limit]
    return csv_response(
        "execution_venue_events.csv",
        [
            "id",
            "created_at",
            "venue",
            "event_type",
            "venue_status",
            "status_bucket",
            "reconcile_state",
            "symbol",
            "client_order_id",
            "venue_order_id",
            "ret_code",
            "ret_msg",
            "incident_type",
            "severity",
            "retryable",
            "suggested_action",
        ],
        venue_events_csv_rows(page, intent_queue_service),
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
