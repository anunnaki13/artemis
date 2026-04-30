from decimal import Decimal

from fastapi import APIRouter, Query

from app.config import get_settings
from app.schemas.risk import CapitalProfileResponse, SignalRiskEvaluateRequest, SignalRiskEvaluateResponse
from services.risk.capital_profile import CapitalProfileManager
from services.risk.signal_gate import SignalRiskGate, SignalRiskInput

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


@router.post("/evaluate-signal", response_model=SignalRiskEvaluateResponse)
async def evaluate_signal(payload: SignalRiskEvaluateRequest) -> SignalRiskEvaluateResponse:
    settings = get_settings()
    manager = CapitalProfileManager(settings.capital_profiles_path)
    capital_profile = manager.evaluate(payload.current_equity)
    decision = SignalRiskGate().evaluate(
        SignalRiskInput(
            signal=payload.signal,
            current_equity=payload.current_equity,
            entry_price=payload.entry_price,
            proposed_notional=payload.proposed_notional,
            current_open_positions=payload.current_open_positions,
            daily_pnl_pct=payload.daily_pnl_pct,
            leverage=payload.leverage,
            quote_volume_usd=payload.quote_volume_usd,
            use_futures=payload.use_futures,
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
    )
