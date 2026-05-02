from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import sqrt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import BacktestRun, Candle, User
from app.schemas.backtest import (
    BacktestGroupRead,
    BacktestOverviewRead,
    BacktestRunRead,
    BacktestRunRequest,
    BacktestWalkForwardRead,
    BacktestWalkForwardRequest,
    BacktestWalkForwardWindowRead,
)
from services.market_data.bybit import BybitMarketDataClient, parse_kline

router = APIRouter(prefix="/backtest", tags=["backtest"])


def to_read(run: BacktestRun) -> BacktestRunRead:
    return BacktestRunRead(
        id=int(run.id),
        created_at=run.created_at,
        status=run.status,
        symbol=run.symbol,
        timeframe=run.timeframe,
        strategy_name=run.strategy_name,
        sample_size=run.sample_size,
        summary_payload=run.summary_payload,
        notes=run.notes,
    )


async def ensure_candles(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    limit: int,
) -> list[Candle]:
    normalized_symbol = symbol.upper()
    query = (
        select(Candle)
        .where(Candle.symbol == normalized_symbol, Candle.timeframe == timeframe)
        .order_by(Candle.open_time.desc())
        .limit(limit)
    )
    candles = list((await session.scalars(query)).all())
    latest_open_time = candles[0].open_time if candles else None
    should_refresh = latest_open_time is None or latest_open_time < datetime.now(UTC) - timedelta(minutes=5) or len(candles) < min(limit, 60)
    if should_refresh:
        client = BybitMarketDataClient()
        klines = await client.klines(normalized_symbol, timeframe, limit, category="spot")
        for kline in klines:
            values = parse_kline(normalized_symbol, timeframe, kline)
            statement = insert(Candle).values(**values)
            await session.execute(
                statement.on_conflict_do_update(
                    constraint="uq_candles_symbol_timeframe_open_time",
                    set_=values,
                )
            )
        await session.commit()
        candles = list((await session.scalars(query)).all())
    return list(reversed(candles))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return sqrt(variance)


def _to_decimal(value: object | None, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def summarize_common_metrics(candles: list[Candle]) -> dict[str, object]:
    closes = [Decimal(item.close) for item in candles]
    opens = [Decimal(item.open) for item in candles]
    high_price = max(Decimal(item.high) for item in candles)
    low_price = min(Decimal(item.low) for item in candles)
    close_change_pcts: list[float] = []
    for previous, current in zip(closes, closes[1:], strict=False):
        if previous == Decimal("0"):
            close_change_pcts.append(0.0)
        else:
            close_change_pcts.append(float(((current - previous) / previous) * Decimal("100")))
    average_range_pct = (
        sum(
            (((Decimal(item.high) - Decimal(item.low)) / Decimal(item.open)) * Decimal("100")) if Decimal(item.open) != Decimal("0") else Decimal("0")
            for item in candles
        )
        / Decimal(len(candles))
    )
    peak_close = closes[0]
    max_drawdown_pct = Decimal("0")
    cumulative_directional_move = Decimal("0")
    for previous, current in zip(closes, closes[1:], strict=False):
        if current > peak_close:
            peak_close = current
        if peak_close != Decimal("0"):
            drawdown_pct = ((peak_close - current) / peak_close) * Decimal("100")
            if drawdown_pct > max_drawdown_pct:
                max_drawdown_pct = drawdown_pct
        cumulative_directional_move += abs(current - previous)
    positive_candles = sum(1 for change in close_change_pcts if change > 0)
    start_price = closes[0]
    end_price = closes[-1]
    trend_efficiency_pct = (
        (abs(end_price - start_price) / cumulative_directional_move) * Decimal("100")
        if cumulative_directional_move != Decimal("0")
        else Decimal("0")
    )
    return {
        "high_price": str(high_price),
        "low_price": str(low_price),
        "average_range_pct": str(average_range_pct),
        "average_close_change_pct": str(Decimal(str(_mean(close_change_pcts)))),
        "volatility_pct": str(Decimal(str(_stdev(close_change_pcts)))),
        "positive_candles_pct": str(
            (Decimal(positive_candles) / Decimal(max(len(close_change_pcts), 1))) * Decimal("100")
        ),
        "max_drawdown_pct": str(max_drawdown_pct),
        "trend_efficiency_pct": str(trend_efficiency_pct),
        "open_to_close_bias_pct": str(
            (sum((close - open_) for close, open_ in zip(closes, opens, strict=False)) / Decimal(len(closes)))
            / start_price
            * Decimal("100")
            if start_price != Decimal("0")
            else Decimal("0")
        ),
    }


def summarize_buy_and_hold(symbol: str, timeframe: str, strategy_name: str, candles: list[Candle]) -> dict[str, object]:
    if len(candles) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="not enough candles for backtest")
    start = candles[0]
    end = candles[-1]
    start_price = Decimal(start.close)
    end_price = Decimal(end.close)
    return_pct = ((end_price - start_price) / start_price) * Decimal("100") if start_price != Decimal("0") else Decimal("0")
    realized_pnl_quote = end_price - start_price
    common = summarize_common_metrics(candles)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "strategy_name": strategy_name,
        "sample_size": len(candles),
        "start_time": start.open_time.isoformat(),
        "end_time": end.close_time.isoformat(),
        "start_price": str(start_price),
        "end_price": str(end_price),
        "return_pct": str(return_pct),
        "realized_pnl_quote": str(realized_pnl_quote),
        "benchmark": "buy_and_hold",
        **common,
    }


def summarize_range_probe(symbol: str, timeframe: str, strategy_name: str, candles: list[Candle]) -> dict[str, object]:
    if len(candles) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="not enough candles for range_probe")
    closes = [Decimal(item.close) for item in candles]
    trades: list[Decimal] = []
    trade_return_pcts: list[Decimal] = []
    for previous_close, entry_close, exit_close in zip(closes, closes[1:], closes[2:], strict=False):
        if entry_close < previous_close:
            pnl = exit_close - entry_close
            trades.append(pnl)
            if entry_close != Decimal("0"):
                trade_return_pcts.append((pnl / entry_close) * Decimal("100"))
    gross_profit_quote = sum((trade for trade in trades if trade > 0), start=Decimal("0"))
    gross_loss_quote = sum((trade for trade in trades if trade < 0), start=Decimal("0"))
    realized_pnl_quote = gross_profit_quote + gross_loss_quote
    winning_trades = sum(1 for trade in trades if trade > 0)
    trades_count = len(trades)
    win_rate = (Decimal(winning_trades) / Decimal(trades_count) * Decimal("100")) if trades_count > 0 else Decimal("0")
    average_trade_return_pct = (
        sum(trade_return_pcts, start=Decimal("0")) / Decimal(len(trade_return_pcts))
        if trade_return_pcts
        else Decimal("0")
    )
    start = candles[0]
    end = candles[-1]
    start_price = Decimal(start.close)
    end_price = Decimal(end.close)
    common = summarize_common_metrics(candles)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "strategy_name": strategy_name,
        "sample_size": len(candles),
        "start_time": start.open_time.isoformat(),
        "end_time": end.close_time.isoformat(),
        "start_price": str(start_price),
        "end_price": str(end_price),
        "return_pct": str((realized_pnl_quote / start_price) * Decimal("100") if start_price != Decimal("0") else Decimal("0")),
        "realized_pnl_quote": str(realized_pnl_quote),
        "benchmark": "range_probe",
        "trades_count": trades_count,
        "winning_trades": winning_trades,
        "win_rate_pct": str(win_rate),
        "average_trade_return_pct": str(average_trade_return_pct),
        "gross_profit_quote": str(gross_profit_quote),
        "gross_loss_quote": str(gross_loss_quote),
        **common,
    }


def build_group_summary(group_key: str, runs: list[BacktestRun]) -> BacktestGroupRead:
    returns = [_to_decimal(run.summary_payload.get("return_pct")) for run in runs]
    ranges = [_to_decimal(run.summary_payload.get("average_range_pct")) for run in runs]
    drawdowns = [_to_decimal(run.summary_payload.get("max_drawdown_pct")) for run in runs]
    volatilities = [_to_decimal(run.summary_payload.get("volatility_pct")) for run in runs]
    sample_sizes = [Decimal(run.sample_size) for run in runs]
    count = Decimal(len(runs))
    return BacktestGroupRead(
        group_key=group_key,
        runs_count=len(runs),
        average_return_pct=sum(returns, start=Decimal("0")) / count,
        best_return_pct=max(returns),
        worst_return_pct=min(returns),
        average_range_pct=sum(ranges, start=Decimal("0")) / count,
        average_drawdown_pct=sum(drawdowns, start=Decimal("0")) / count,
        average_volatility_pct=sum(volatilities, start=Decimal("0")) / count,
        average_sample_size=sum(sample_sizes, start=Decimal("0")) / count,
    )


def summarize_strategy_window(symbol: str, timeframe: str, strategy_name: str, candles: list[Candle]) -> dict[str, object]:
    if strategy_name == "range_probe":
        return summarize_range_probe(symbol, timeframe, strategy_name, candles)
    return summarize_buy_and_hold(symbol, timeframe, strategy_name, candles)


@router.post("/runs", response_model=BacktestRunRead)
async def run_backtest(
    payload: BacktestRunRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BacktestRunRead:
    if payload.strategy_name not in {"buy_and_hold", "range_probe"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported strategy_name")
    candles = await ensure_candles(session, payload.symbol, payload.timeframe, payload.limit)
    summary = summarize_strategy_window(payload.symbol.upper(), payload.timeframe, payload.strategy_name, candles)
    run = BacktestRun(
        status="completed",
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        strategy_name=payload.strategy_name,
        sample_size=len(candles),
        summary_payload=summary,
        notes=payload.notes,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return to_read(run)


@router.get("/runs", response_model=list[BacktestRunRead])
async def list_backtest_runs(
    limit: int = Query(default=20, ge=1, le=100),
    symbol: str | None = Query(default=None),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BacktestRunRead]:
    query = select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit)
    if symbol:
        query = query.where(BacktestRun.symbol == symbol.upper())
    runs = list((await session.scalars(query)).all())
    return [to_read(run) for run in runs]


@router.post("/walk-forward", response_model=BacktestWalkForwardRead)
async def run_walk_forward(
    payload: BacktestWalkForwardRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BacktestWalkForwardRead:
    if payload.strategy_name not in {"buy_and_hold", "range_probe"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported strategy_name")
    if payload.train_size + payload.test_size > payload.lookback_limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="lookback_limit must cover train_size + test_size")

    candles = await ensure_candles(session, payload.symbol, payload.timeframe, payload.lookback_limit)
    if len(candles) < payload.train_size + payload.test_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="not enough candles for walk-forward run")

    windows: list[BacktestWalkForwardWindowRead] = []
    cursor = payload.train_size
    window_index = 1
    while cursor + payload.test_size <= len(candles):
        train_slice = candles[cursor - payload.train_size : cursor]
        test_slice = candles[cursor : cursor + payload.test_size]
        if len(train_slice) < payload.train_size or len(test_slice) < payload.test_size:
            break
        summary = summarize_strategy_window(payload.symbol.upper(), payload.timeframe, payload.strategy_name, test_slice)
        trades_count_value = summary.get("trades_count")
        win_rate_value = summary.get("win_rate_pct")
        windows.append(
            BacktestWalkForwardWindowRead(
                window_index=window_index,
                train_start=train_slice[0].open_time,
                train_end=train_slice[-1].close_time,
                test_start=test_slice[0].open_time,
                test_end=test_slice[-1].close_time,
                return_pct=_to_decimal(summary.get("return_pct")),
                max_drawdown_pct=_to_decimal(summary.get("max_drawdown_pct")),
                volatility_pct=_to_decimal(summary.get("volatility_pct")),
                trades_count=int(str(trades_count_value)) if trades_count_value is not None else None,
                win_rate_pct=_to_decimal(win_rate_value) if win_rate_value is not None else None,
            )
        )
        cursor += payload.step_size
        window_index += 1

    if not windows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="walk-forward produced no windows")

    returns = [item.return_pct for item in windows]
    drawdowns = [item.max_drawdown_pct for item in windows]
    volatilities = [item.volatility_pct for item in windows]
    win_rates = [item.win_rate_pct for item in windows if item.win_rate_pct is not None]
    count = Decimal(len(windows))
    return BacktestWalkForwardRead(
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        strategy_name=payload.strategy_name,
        lookback_limit=payload.lookback_limit,
        train_size=payload.train_size,
        test_size=payload.test_size,
        step_size=payload.step_size,
        windows_count=len(windows),
        positive_windows_count=sum(1 for item in windows if item.return_pct > Decimal("0")),
        average_return_pct=sum(returns, start=Decimal("0")) / count,
        best_return_pct=max(returns),
        worst_return_pct=min(returns),
        average_drawdown_pct=sum(drawdowns, start=Decimal("0")) / count,
        average_volatility_pct=sum(volatilities, start=Decimal("0")) / count,
        average_win_rate_pct=(sum(win_rates, start=Decimal("0")) / Decimal(len(win_rates))) if win_rates else None,
        windows=windows,
    )


@router.get("/overview", response_model=BacktestOverviewRead)
async def get_backtest_overview(
    symbol: str = Query(default="BTCUSDT"),
    strategy_name: str | None = Query(default=None),
    timeframe: str | None = Query(default=None),
    limit: int = Query(default=100, ge=10, le=500),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BacktestOverviewRead:
    normalized_symbol = symbol.upper()
    query = (
        select(BacktestRun)
        .where(BacktestRun.symbol == normalized_symbol)
        .order_by(BacktestRun.created_at.desc())
        .limit(limit)
    )
    if strategy_name:
        query = query.where(BacktestRun.strategy_name == strategy_name)
    if timeframe:
        query = query.where(BacktestRun.timeframe == timeframe)
    runs = list((await session.scalars(query)).all())
    strategy_groups_map: dict[str, list[BacktestRun]] = {}
    timeframe_groups_map: dict[str, list[BacktestRun]] = {}
    for run in runs:
        strategy_groups_map.setdefault(run.strategy_name, []).append(run)
        timeframe_groups_map.setdefault(run.timeframe, []).append(run)
    strategy_groups = sorted(
        (build_group_summary(key, group) for key, group in strategy_groups_map.items()),
        key=lambda item: item.average_return_pct,
        reverse=True,
    )
    timeframe_groups = sorted(
        (build_group_summary(key, group) for key, group in timeframe_groups_map.items()),
        key=lambda item: item.average_return_pct,
        reverse=True,
    )
    return BacktestOverviewRead(
        symbol=normalized_symbol,
        filtered_runs_count=len(runs),
        available_strategies=sorted(strategy_groups_map.keys()),
        available_timeframes=sorted(timeframe_groups_map.keys()),
        strategy_groups=strategy_groups,
        timeframe_groups=timeframe_groups,
    )
