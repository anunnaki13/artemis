from dataclasses import dataclass
from decimal import Decimal

from app.schemas.risk import CapitalProfileResponse
from strategies.base import Signal


@dataclass(frozen=True)
class SignalRiskInput:
    signal: Signal
    current_equity: Decimal
    entry_price: Decimal
    proposed_notional: Decimal
    current_open_positions: int
    daily_pnl_pct: Decimal
    leverage: Decimal
    quote_volume_usd: Decimal | None
    use_futures: bool


@dataclass(frozen=True)
class SignalRiskDecision:
    allowed: bool
    reasons: list[str]
    recommended_max_notional: Decimal
    recommended_risk_amount: Decimal
    computed_r_multiple: Decimal | None
    profile_name: str


class SignalRiskGate:
    def evaluate(
        self,
        payload: SignalRiskInput,
        capital_profile: CapitalProfileResponse,
    ) -> SignalRiskDecision:
        reasons: list[str] = []
        profile = capital_profile.active_profile

        recommended_max_notional = payload.current_equity * Decimal("0.10")
        recommended_risk_amount = payload.current_equity * (profile.risk_per_trade_pct / Decimal("100"))

        if payload.current_open_positions >= profile.max_concurrent_positions:
            reasons.append("max concurrent positions reached for active capital profile")

        if payload.proposed_notional > recommended_max_notional:
            reasons.append("proposed notional exceeds hard max position size")

        if payload.leverage > Decimal("3"):
            reasons.append("proposed leverage exceeds hard max leverage")

        if payload.daily_pnl_pct <= Decimal("-0.05"):
            reasons.append("daily pnl breaches absolute max daily loss")

        if payload.signal.source in profile.forbidden_strategies:
            reasons.append("strategy is forbidden for active capital profile")

        if payload.use_futures and profile.use_futures is False:
            reasons.append("futures usage is blocked for active capital profile")

        if (
            payload.quote_volume_usd is not None
            and payload.quote_volume_usd < profile.avoid_pairs_below_volume
        ):
            reasons.append("symbol liquidity is below profile minimum")

        r_multiple = self._compute_r_multiple(payload.signal, payload.entry_price)
        if r_multiple is None:
            reasons.append("missing stop-loss or take-profit for R validation")
        elif r_multiple < profile.min_trade_target_r:
            reasons.append("trade target R is below capital profile minimum")

        return SignalRiskDecision(
            allowed=len(reasons) == 0,
            reasons=reasons,
            recommended_max_notional=recommended_max_notional,
            recommended_risk_amount=recommended_risk_amount,
            computed_r_multiple=r_multiple,
            profile_name=profile.name,
        )

    def _compute_r_multiple(self, signal: Signal, entry_price: Decimal) -> Decimal | None:
        if signal.suggested_stop is None or signal.suggested_take_profit is None:
            return None
        stop_price = Decimal(str(signal.suggested_stop))
        take_profit_price = Decimal(str(signal.suggested_take_profit))
        if signal.side == "long":
            risk = entry_price - stop_price
            reward = take_profit_price - entry_price
        else:
            risk = stop_price - entry_price
            reward = entry_price - take_profit_price
        if risk <= Decimal("0") or reward <= Decimal("0"):
            return None
        return reward / risk
