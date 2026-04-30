from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def summary() -> dict[str, object]:
    return {
        "equity": {"net": 0, "currency": "USDT"},
        "daily_pnl": {"net": 0, "gross": 0},
        "bot_status": "PAUSED",
        "market_regime": "UNKNOWN",
    }

