from fastapi import APIRouter

from app.config import get_settings
from app.schemas.edge import UniverseCandidateRead, UniverseRefreshResponse
from services.edge.universe_manager import SymbolUniverseManager
from services.market_data.binance import BinanceMarketDataClient

router = APIRouter(prefix="/edge", tags=["edge"])


@router.post("/universe/refresh", response_model=UniverseRefreshResponse)
async def refresh_universe() -> UniverseRefreshResponse:
    settings = get_settings()
    tickers = await BinanceMarketDataClient().ticker_24h()
    selection = SymbolUniverseManager(
        settings.universe_config_path,
        settings.universe_blacklist_path,
    ).select(tickers)
    return UniverseRefreshResponse(
        candidates=[UniverseCandidateRead.model_validate(candidate.__dict__) for candidate in selection.candidates],
        candidate_count=len(selection.candidates),
        rejected_count=selection.rejected_count,
        min_quote_volume_usd=selection.min_quote_volume_usd,
        max_quote_volume_usd=selection.max_quote_volume_usd,
    )
