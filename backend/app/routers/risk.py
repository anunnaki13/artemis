from fastapi import APIRouter

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/policy")
async def policy() -> dict[str, object]:
    return {
        "risk_per_trade": 0.005,
        "max_daily_loss": 0.02,
        "hard_limits": {
            "max_position_pct": 0.10,
            "max_total_exposure_pct": 1.00,
            "max_leverage": 3.0,
            "absolute_max_daily_loss": 0.05,
        },
    }

