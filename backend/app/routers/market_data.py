from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.db import get_session
from app.deps import get_current_user
from app.models import Candle, MarketSnapshot, OrderBookSnapshot, Symbol, User
from app.schemas.market_data import (
    CandleIngestRequest,
    CandleIngestResponse,
    CandleRead,
    LiquidityMetricsPointResponse,
    MarketStreamStartRequest,
    MarketStreamStatusResponse,
    OrderBookLevel,
    OrderBookMetricsResponse,
    OrderBookSnapshotPointResponse,
    OrderBookStateResponse,
    SymbolRead,
    SyncSymbolsResponse,
)
from services.market_data.binance import BinanceMarketDataClient, extract_symbol_filters, parse_kline
from services.market_data.orderbook import levels_from_payload, metrics_from_payload
from services.market_data.streaming import BinanceMarketStreamService

router = APIRouter(prefix="/market-data", tags=["market-data"])
stream_service = BinanceMarketStreamService(session_factory=AsyncSessionLocal)


def build_orderbook_metrics_response(metrics: Any) -> OrderBookMetricsResponse:
    return OrderBookMetricsResponse(
        spread=metrics.spread,
        spread_bps=metrics.spread_bps,
        mid_price=metrics.mid_price,
        bid_depth_notional_0p5pct=metrics.bid_depth_notional_0p5pct,
        ask_depth_notional_0p5pct=metrics.ask_depth_notional_0p5pct,
        imbalance_ratio_0p5pct=metrics.imbalance_ratio_0p5pct,
        best_bid=metrics.best_bid,
        best_ask=metrics.best_ask,
        last_update_id=metrics.last_update_id,
        updated_at=metrics.updated_at,
    )


def build_orderbook_snapshot_response(snapshot: OrderBookSnapshot) -> OrderBookSnapshotPointResponse:
    parsed_metrics = metrics_from_payload({"metrics": snapshot.metrics}, snapshot.timestamp)
    if parsed_metrics is None:
        raise ValueError(f"invalid persisted metrics payload for {snapshot.symbol}")
    return OrderBookSnapshotPointResponse(
        symbol=snapshot.symbol,
        timestamp=snapshot.timestamp,
        bids=levels_from_payload(snapshot.bids),
        asks=levels_from_payload(snapshot.asks),
        metrics=build_orderbook_metrics_response(parsed_metrics),
    )


@router.get("/symbols", response_model=list[SymbolRead])
async def list_symbols(
    quote_asset: str | None = Query(default=None, min_length=2, max_length=16),
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[Symbol]:
    query = select(Symbol).order_by(Symbol.symbol).limit(limit)
    if quote_asset is not None:
        query = query.where(Symbol.quote_asset == quote_asset.upper())
    return list((await session.scalars(query)).all())


@router.post("/symbols/sync", response_model=SyncSymbolsResponse)
async def sync_symbols(
    quote_asset: str | None = Query(default="USDT", min_length=2, max_length=16),
    limit: int = Query(default=500, ge=1, le=2000),
    session: AsyncSession = Depends(get_session),
) -> SyncSymbolsResponse:
    client = BinanceMarketDataClient()
    payload = await client.exchange_info()
    symbols = [
        item
        for item in payload.get("symbols", [])
        if isinstance(item, dict)
        and item.get("status") == "TRADING"
        and (quote_asset is None or item.get("quoteAsset") == quote_asset.upper())
    ][:limit]

    for item in symbols:
        filters = extract_symbol_filters(item)
        values: dict[str, Any] = {
            "symbol": item["symbol"],
            "base_asset": item["baseAsset"],
            "quote_asset": item["quoteAsset"],
            "market_type": "spot",
            "status": item["status"],
            "is_enabled": True,
            **filters,
        }
        statement = insert(Symbol).values(**values)
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[Symbol.symbol],
                set_=values,
            )
        )
    await session.commit()
    return SyncSymbolsResponse(synced=len(symbols), quote_asset=quote_asset.upper() if quote_asset else None)


@router.post("/candles/ingest", response_model=CandleIngestResponse)
async def ingest_candles(
    payload: CandleIngestRequest,
    session: AsyncSession = Depends(get_session),
) -> CandleIngestResponse:
    client = BinanceMarketDataClient()
    klines = await client.klines(payload.symbol, payload.interval, payload.limit)
    for kline in klines:
        values = parse_kline(payload.symbol, payload.interval, kline)
        statement = insert(Candle).values(**values)
        await session.execute(
            statement.on_conflict_do_update(
                constraint="uq_candles_symbol_timeframe_open_time",
                set_=values,
            )
        )
    await session.commit()
    return CandleIngestResponse(
        symbol=payload.symbol.upper(),
        interval=payload.interval,
        ingested=len(klines),
    )


@router.get("/candles", response_model=list[CandleRead])
async def list_candles(
    symbol: str = Query(default="BTCUSDT", min_length=3, max_length=32),
    interval: str = Query(default="1m", min_length=1, max_length=8),
    limit: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[Candle]:
    query = (
        select(Candle)
        .where(Candle.symbol == symbol.upper(), Candle.timeframe == interval)
        .order_by(Candle.open_time.desc())
        .limit(limit)
    )
    return list((await session.scalars(query)).all())


@router.get("/stream/status", response_model=MarketStreamStatusResponse)
async def market_stream_status(_: User = Depends(get_current_user)) -> MarketStreamStatusResponse:
    status_payload = stream_service.status()
    return MarketStreamStatusResponse(
        running=status_payload.running,
        symbols=status_payload.symbols,
        interval=status_payload.interval,
        reconnect_attempts=status_payload.reconnect_attempts,
        messages_processed=status_payload.messages_processed,
        poll_cycles=status_payload.poll_cycles,
        last_message_at=status_payload.last_message_at,
        last_error=status_payload.last_error,
    )


@router.post("/stream/start", response_model=MarketStreamStatusResponse)
async def start_market_stream(
    payload: MarketStreamStartRequest,
    _: User = Depends(get_current_user),
) -> MarketStreamStatusResponse:
    try:
        status_payload = await stream_service.start(payload.symbols, payload.interval)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MarketStreamStatusResponse(
        running=status_payload.running,
        symbols=status_payload.symbols,
        interval=status_payload.interval,
        reconnect_attempts=status_payload.reconnect_attempts,
        messages_processed=status_payload.messages_processed,
        poll_cycles=status_payload.poll_cycles,
        last_message_at=status_payload.last_message_at,
        last_error=status_payload.last_error,
    )


@router.post("/stream/stop", response_model=MarketStreamStatusResponse)
async def stop_market_stream(_: User = Depends(get_current_user)) -> MarketStreamStatusResponse:
    status_payload = await stream_service.stop()
    return MarketStreamStatusResponse(
        running=status_payload.running,
        symbols=status_payload.symbols,
        interval=status_payload.interval,
        reconnect_attempts=status_payload.reconnect_attempts,
        messages_processed=status_payload.messages_processed,
        poll_cycles=status_payload.poll_cycles,
        last_message_at=status_payload.last_message_at,
        last_error=status_payload.last_error,
    )


@router.get("/orderbook/{symbol}", response_model=OrderBookStateResponse)
async def get_orderbook(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=50),
    _: User = Depends(get_current_user),
) -> OrderBookStateResponse:
    orderbook = stream_service.orderbook(symbol)
    if orderbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"orderbook for {symbol.upper()} is not available",
        )
    metrics = orderbook.metrics()
    return OrderBookStateResponse(
        symbol=symbol.upper(),
        bids=[OrderBookLevel(price=level.price, quantity=level.quantity) for level in orderbook.top_bids(limit)],
        asks=[OrderBookLevel(price=level.price, quantity=level.quantity) for level in orderbook.top_asks(limit)],
        metrics=build_orderbook_metrics_response(metrics),
    )


@router.get("/liquidity/{symbol}/latest", response_model=LiquidityMetricsPointResponse)
async def get_latest_liquidity_metrics(
    symbol: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> LiquidityMetricsPointResponse:
    query = (
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == symbol.upper())
        .order_by(MarketSnapshot.timestamp.desc())
        .limit(200)
    )
    snapshots = list((await session.scalars(query)).all())
    for snapshot in snapshots:
        payload = snapshot.payload if isinstance(snapshot.payload, dict) else None
        if payload is None:
            continue
        metrics = metrics_from_payload(payload, snapshot.timestamp)
        if metrics is None:
            continue
        return LiquidityMetricsPointResponse(
            symbol=symbol.upper(),
            timestamp=snapshot.timestamp,
            metrics=build_orderbook_metrics_response(metrics),
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"liquidity metrics for {symbol.upper()} are not available",
    )


@router.get("/liquidity/{symbol}/history", response_model=list[LiquidityMetricsPointResponse])
async def get_liquidity_metrics_history(
    symbol: str,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[LiquidityMetricsPointResponse]:
    query = (
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == symbol.upper())
        .order_by(MarketSnapshot.timestamp.desc())
        .limit(min(limit * 5, 1000))
    )
    snapshots = list((await session.scalars(query)).all())
    points: list[LiquidityMetricsPointResponse] = []
    for snapshot in snapshots:
        payload = snapshot.payload if isinstance(snapshot.payload, dict) else None
        if payload is None:
            continue
        metrics = metrics_from_payload(payload, snapshot.timestamp)
        if metrics is None:
            continue
        points.append(
            LiquidityMetricsPointResponse(
                symbol=symbol.upper(),
                timestamp=snapshot.timestamp,
                metrics=build_orderbook_metrics_response(metrics),
            )
        )
        if len(points) >= limit:
            break
    return list(reversed(points))


@router.get("/orderbook/{symbol}/snapshots", response_model=list[OrderBookSnapshotPointResponse])
async def get_orderbook_snapshot_history(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[OrderBookSnapshotPointResponse]:
    query = (
        select(OrderBookSnapshot)
        .where(OrderBookSnapshot.symbol == symbol.upper())
        .order_by(OrderBookSnapshot.timestamp.desc())
        .limit(limit)
    )
    snapshots = list((await session.scalars(query)).all())
    return [build_orderbook_snapshot_response(snapshot) for snapshot in reversed(snapshots)]
