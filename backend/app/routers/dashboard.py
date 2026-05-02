import csv
import io
from decimal import Decimal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import (
    ExecutionIntent,
    ExecutionVenueEvent,
    MarketSnapshot,
    SpotAccountBalance,
    SpotExecutionFill,
    SpotSymbolPosition,
    User,
)
from services.execution.account_state import SpotAccountStateService
from services.execution.fill_analytics import summarize_intent_lineage_outcomes, summarize_strategy_quality
from services.execution.intent_queue import ExecutionIntentQueueService
from services.market_data.orderbook import metrics_from_payload
from services.reports.daily_digest import DailyDigestService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
intent_queue_service = ExecutionIntentQueueService()
account_state_service = SpotAccountStateService()
digest_service = DailyDigestService()


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


@router.get("/summary")
async def summary(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> dict[str, object]:
    from app.routers.execution import user_stream_service
    from app.routers.market_data import stream_service

    recent_intents = list(
        (
            await session.scalars(
                select(ExecutionIntent)
                .order_by(ExecutionIntent.created_at.desc())
                .limit(25)
            )
        ).all()
    )
    lineage_intents = list(
        (
            await session.scalars(
                select(ExecutionIntent)
                .order_by(ExecutionIntent.created_at.desc())
                .limit(100)
            )
        ).all()
    )
    status_counts = {
        "queued": 0,
        "approved": 0,
        "dispatching": 0,
        "executed": 0,
        "failed": 0,
        "cancelled": 0,
        "rejected": 0,
    }
    exposure = Decimal("0")
    for intent in recent_intents:
        if intent.status in status_counts:
            status_counts[intent.status] += 1
        if intent.status in {"approved", "dispatching"}:
            exposure += intent.approved_notional

    latest_liquidity = None
    liquidity_rows = list(
        (
            await session.scalars(
                select(MarketSnapshot)
                .where(MarketSnapshot.symbol == "BTCUSDT")
                .order_by(MarketSnapshot.timestamp.desc())
                .limit(50)
            )
        ).all()
    )
    for row in liquidity_rows:
        payload = row.payload if isinstance(row.payload, dict) else None
        if payload is None:
            continue
        metrics = metrics_from_payload(payload, row.timestamp)
        if metrics is None:
            continue
        latest_liquidity = {
            "symbol": "BTCUSDT",
            "timestamp": row.timestamp,
            "spread_bps": metrics.spread_bps,
            "imbalance_ratio": metrics.imbalance_ratio_0p5pct,
            "best_bid": metrics.best_bid,
            "best_ask": metrics.best_ask,
            "bid_depth_notional": metrics.bid_depth_notional_0p5pct,
            "ask_depth_notional": metrics.ask_depth_notional_0p5pct,
        }
        break

    market_stream = stream_service.status()
    user_stream = user_stream_service.status()
    bot_status = "RUNNING" if market_stream.running else "PAUSED"
    if user_stream.running and user_stream.subscribed:
        execution_status = "LIVE SYNC"
    elif user_stream.running:
        execution_status = "CONNECTING"
    else:
        execution_status = "IDLE"

    balances = list(
        (
            await session.scalars(
                select(SpotAccountBalance)
                .order_by(SpotAccountBalance.total_value_usd.desc().nullslast(), SpotAccountBalance.asset.asc())
                .limit(5)
            )
        ).all()
    )
    equity = sum((balance.total_value_usd or Decimal("0")) for balance in balances)
    positions = list(
        (
            await session.scalars(
                select(SpotSymbolPosition)
                .order_by(SpotSymbolPosition.quote_exposure_usd.desc().nullslast(), SpotSymbolPosition.symbol.asc())
                .limit(5)
            )
        ).all()
    )
    await account_state_service.refresh_all_position_marks(session, positions)
    fills = list(
        (
            await session.scalars(
                select(SpotExecutionFill)
                .order_by(SpotExecutionFill.filled_at.desc())
                .limit(250)
            )
        ).all()
    )
    await session.commit()
    total_unrealized_pnl = sum((position.unrealized_pnl_usd or Decimal("0")) for position in positions)
    total_realized_pnl = sum(position.realized_pnl_usd for position in positions)
    strategy_breakdown = summarize_strategy_quality(fills)[:5]
    lineage_outcomes = summarize_intent_lineage_outcomes(lineage_intents, fills)
    replacement_lineages = [item for item in lineage_outcomes if item.lineage_size > 1]
    replacement_alerts = [
        item
        for item in replacement_lineages
        if (item.slippage_bps is not None and item.slippage_bps > Decimal("5")) or item.fill_ratio < Decimal("0.9")
    ][:5]
    digest_run_rows = await digest_service.list_run_logs(session, 3)
    digest_alert = next((item for item in digest_run_rows if item.anomaly_score > 0), None)
    recent_venue_events = list(
        (
            await session.scalars(
                select(ExecutionVenueEvent)
                .order_by(ExecutionVenueEvent.created_at.desc())
                .limit(50)
            )
        ).all()
    )
    venue_event_summary = {
        "accepted": 0,
        "partial": 0,
        "filled": 0,
        "cancelled": 0,
        "rejected": 0,
        "pending": 0,
        "unknown": 0,
    }
    for event in recent_venue_events:
        status_bucket = intent_queue_service.classify_venue_status(event.venue_status)
        venue_event_summary[status_bucket] += 1
    filtered_venue_events = [
        event
        for event in recent_venue_events
        if intent_queue_service.classify_venue_status(event.venue_status) in {"partial", "cancelled", "rejected"}
    ][:6]

    return {
        "equity": {"net": equity, "currency": "USDT"},
        "daily_pnl": {"net": total_unrealized_pnl, "gross": total_realized_pnl},
        "weekly_pnl": {"net": 0, "gross": 0},
        "bot_status": bot_status,
        "market_regime": "MICROSTRUCTURE" if latest_liquidity is not None else "UNKNOWN",
        "execution_status": execution_status,
        "exposure_notional": exposure,
        "execution_counts": status_counts,
        "recent_intents": [
            {
                "id": int(intent.id),
                "symbol": intent.symbol,
                "status": intent.status,
                "source_strategy": intent.source_strategy,
                "approved_notional": intent.approved_notional,
                "created_at": intent.created_at,
                "notes": intent.notes,
            }
            for intent in recent_intents[:8]
        ],
        "strategy_breakdown": [
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
            }
            for item in strategy_breakdown
        ],
        "lineage_summary": {
            "replacement_lineages_count": len(replacement_lineages),
            "replacement_alerts_count": len(replacement_alerts),
            "worst_slippage_bps": max(
                (
                    item.slippage_bps
                    for item in replacement_lineages
                    if item.slippage_bps is not None
                ),
                default=None,
            ),
        },
        "lineage_alerts": [
            {
                "root_intent_id": item.root_intent_id,
                "latest_intent_id": item.latest_intent_id,
                "symbol": item.symbol,
                "source_strategy": item.source_strategy,
                "lineage_size": item.lineage_size,
                "lineage_statuses": item.lineage_statuses,
                "fill_ratio": item.fill_ratio,
                "slippage_bps": item.slippage_bps,
                "realized_pnl_usd": item.realized_pnl_usd,
                "last_fill_at": item.last_fill_at,
            }
            for item in replacement_alerts
        ],
        "venue_event_summary": venue_event_summary,
        "venue_event_alerts": [
            {
                "id": int(event.id),
                "created_at": event.created_at,
                "venue": event.venue,
                "event_type": event.event_type,
                "venue_status": event.venue_status,
                "status_bucket": intent_queue_service.classify_venue_status(event.venue_status),
                "symbol": event.symbol,
                "client_order_id": event.client_order_id,
                "venue_order_id": event.venue_order_id,
                "reconcile_state": event.reconcile_state,
                "ret_code": intent_queue_service.extract_venue_diagnostics(event.payload)[0],
                "ret_msg": intent_queue_service.extract_venue_diagnostics(event.payload)[1],
            }
            for event in filtered_venue_events
        ],
        "digest_runs": [
            {
                "report_date": item.report_date,
                "generated_at": item.generated_at,
                "fills_count": item.fills_count,
                "intents_count": item.intents_count,
                "lineage_alerts_count": item.lineage_alerts_count,
                "top_strategy": item.top_strategy,
                "top_strategy_realized_pnl_usd": (
                    None if item.top_strategy_realized_pnl_usd is None else str(item.top_strategy_realized_pnl_usd)
                ),
                "anomaly_score": item.anomaly_score,
                "anomaly_flags": item.anomaly_flags,
            }
            for item in digest_run_rows
        ],
        "digest_alert": (
            None
            if digest_alert is None
            else {
                "report_date": digest_alert.report_date,
                "anomaly_score": digest_alert.anomaly_score,
                "anomaly_flags": digest_alert.anomaly_flags,
                "fills_count": digest_alert.fills_count,
                "lineage_alerts_count": digest_alert.lineage_alerts_count,
                "top_strategy": digest_alert.top_strategy,
                "top_strategy_realized_pnl_usd": (
                    None
                    if digest_alert.top_strategy_realized_pnl_usd is None
                    else str(digest_alert.top_strategy_realized_pnl_usd)
                ),
            }
        ),
        "market_stream": {
            "running": market_stream.running,
            "symbols": market_stream.symbols,
            "interval": market_stream.interval,
            "messages_processed": market_stream.messages_processed,
            "poll_cycles": market_stream.poll_cycles,
            "last_error": market_stream.last_error,
            "last_message_at": market_stream.last_message_at,
        },
        "user_stream": {
            "running": user_stream.running,
            "subscribed": user_stream.subscribed,
            "messages_processed": user_stream.messages_processed,
            "last_event_type": user_stream.last_event_type,
            "last_error": user_stream.last_error,
            "last_message_at": user_stream.last_message_at,
        },
        "focus_liquidity": latest_liquidity,
        "balances": [
            {
                "asset": balance.asset,
                "free": balance.free,
                "locked": balance.locked,
                "total": balance.total,
                "total_value_usd": balance.total_value_usd,
                "updated_at": balance.updated_at,
            }
            for balance in balances
        ],
        "positions": [
            {
                "symbol": position.symbol,
                "base_asset": position.base_asset,
                "quote_asset": position.quote_asset,
                "net_quantity": position.net_quantity,
                "average_entry_price": position.average_entry_price,
                "last_mark_price": position.last_mark_price,
                "quote_exposure_usd": position.quote_exposure_usd,
                "market_value_usd": position.market_value_usd,
                "realized_notional": position.realized_notional,
                "realized_pnl_usd": position.realized_pnl_usd,
                "unrealized_pnl_usd": position.unrealized_pnl_usd,
                "updated_at": position.updated_at,
            }
            for position in positions
        ],
    }


@router.get("/summary/strategy-breakdown/export")
async def export_dashboard_strategy_breakdown_csv(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    fills = list(
        (
            await session.scalars(
                select(SpotExecutionFill)
                .order_by(SpotExecutionFill.filled_at.desc())
                .limit(250)
            )
        ).all()
    )
    strategy_breakdown = summarize_strategy_quality(fills)
    return csv_response(
        "dashboard-strategy-breakdown.csv",
        [
            "source_strategy",
            "fills_count",
            "chains_count",
            "gross_notional_usd",
            "gross_realized_pnl_usd",
            "win_rate",
        ],
        [
            [
                item.source_strategy,
                item.fills_count,
                item.chains_count,
                item.gross_notional_usd,
                item.gross_realized_pnl_usd,
                item.win_rate,
            ]
            for item in strategy_breakdown
        ],
    )


@router.get("/summary/lineage-alerts/export")
async def export_dashboard_lineage_alerts_csv(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    lineage_intents = list(
        (
            await session.scalars(
                select(ExecutionIntent)
                .order_by(ExecutionIntent.created_at.desc())
                .limit(100)
            )
        ).all()
    )
    fills = list(
        (
            await session.scalars(
                select(SpotExecutionFill)
                .order_by(SpotExecutionFill.filled_at.desc())
                .limit(250)
            )
        ).all()
    )
    lineage_outcomes = summarize_intent_lineage_outcomes(lineage_intents, fills)
    replacement_alerts = [
        item
        for item in lineage_outcomes
        if item.lineage_size > 1
        and ((item.slippage_bps is not None and item.slippage_bps > Decimal("5")) or item.fill_ratio < Decimal("0.9"))
    ]
    return csv_response(
        "dashboard-lineage-alerts.csv",
        [
            "root_intent_id",
            "latest_intent_id",
            "symbol",
            "source_strategy",
            "lineage_size",
            "lineage_statuses",
            "fill_ratio",
            "slippage_bps",
            "realized_pnl_usd",
            "last_fill_at",
        ],
        [
            [
                item.root_intent_id,
                item.latest_intent_id,
                item.symbol,
                item.source_strategy,
                item.lineage_size,
                " | ".join(item.lineage_statuses),
                item.fill_ratio,
                item.slippage_bps,
                item.realized_pnl_usd,
                item.last_fill_at.isoformat() if item.last_fill_at is not None else None,
            ]
            for item in replacement_alerts
        ],
    )
