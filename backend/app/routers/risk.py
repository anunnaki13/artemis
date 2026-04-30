from decimal import Decimal

from fastapi import APIRouter, Query

from app.config import get_settings
from app.schemas.risk import CapitalProfileResponse
from services.risk.capital_profile import CapitalProfileManager

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


@router.get("/capital-profile", response_model=CapitalProfileResponse)
async def capital_profile(
    current_equity: Decimal = Query(default=Decimal("100"), ge=0.0),
) -> CapitalProfileResponse:
    settings = get_settings()
    manager = CapitalProfileManager(settings.capital_profiles_path)
    return manager.evaluate(current_equity)
