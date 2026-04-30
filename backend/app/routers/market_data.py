from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Candle, Symbol
from app.schemas.market_data import (
    CandleIngestRequest,
    CandleIngestResponse,
    CandleRead,
    SymbolRead,
    SyncSymbolsResponse,
)
from services.market_data.binance import BinanceMarketDataClient, extract_symbol_filters, parse_kline

router = APIRouter(prefix="/market-data", tags=["market-data"])


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
