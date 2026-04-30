from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import OrderBookSnapshot, User
from app.schemas.strategy import (
    OrderBookImbalanceDiagnosticsResponse,
    OrderBookImbalanceEvaluateRequest,
    StrategyEvaluationResponse,
)
from services.market_data.orderbook import metrics_from_payload
from services.strategy.orderbook_imbalance import (
    OrderBookImbalanceSnapshot,
    OrderBookImbalanceStrategy,
)

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("/orderbook-imbalance/evaluate", response_model=StrategyEvaluationResponse)
async def evaluate_orderbook_imbalance(
    payload: OrderBookImbalanceEvaluateRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> StrategyEvaluationResponse:
    query = (
        select(OrderBookSnapshot)
        .where(OrderBookSnapshot.symbol == payload.symbol.upper())
        .order_by(OrderBookSnapshot.timestamp.desc())
        .limit(payload.lookback)
    )
    snapshots = list(reversed(list((await session.scalars(query)).all())))
    market_data: list[OrderBookImbalanceSnapshot] = []
    for snapshot in snapshots:
        metrics = metrics_from_payload({"metrics": snapshot.metrics}, snapshot.timestamp)
        if metrics is None:
            continue
        market_data.append(
            OrderBookImbalanceSnapshot(
                symbol=snapshot.symbol,
                timestamp=snapshot.timestamp,
                metrics=metrics,
            )
        )

    if not market_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"orderbook snapshots for {payload.symbol.upper()} are not available",
        )

    strategy = OrderBookImbalanceStrategy()
    params = payload.model_dump()
    signal = await strategy.generate_signal(market_data, params)
    diagnostics = strategy.diagnostics(market_data, params)

    return StrategyEvaluationResponse(
        strategy=strategy.name,
        signal=signal,
        diagnostics=OrderBookImbalanceDiagnosticsResponse(
            sample_size=diagnostics.sample_size,
            latest_timestamp=diagnostics.latest_timestamp,
            latest_imbalance_ratio=diagnostics.latest_imbalance_ratio,
            average_imbalance_ratio=diagnostics.average_imbalance_ratio,
            latest_spread_bps=diagnostics.latest_spread_bps,
            bid_depth_notional_0p5pct=diagnostics.bid_depth_notional_0p5pct,
            ask_depth_notional_0p5pct=diagnostics.ask_depth_notional_0p5pct,
            persistence_ratio_observed=diagnostics.persistence_ratio_observed,
        ),
    )
