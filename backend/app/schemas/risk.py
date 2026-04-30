from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

UseFutures = bool | Literal["optional"]


class CapitalProfileRead(BaseModel):
    name: str
    equity_min: Decimal
    equity_max: Decimal | None
    min_notional_buffer: Decimal
    max_concurrent_positions: int
    risk_per_trade_pct: Decimal
    min_trade_target_r: Decimal
    preferred_fee_tier: str
    stablecoin_only_in_idle: bool
    avoid_pairs_below_volume: Decimal
    use_futures: UseFutures
    forbidden_strategies: list[str]


class FeeStrategyRead(BaseModel):
    default_order_type: str
    taker_fallback_after_seconds: int
    taker_fallback_only_if: str
    use_bnb_for_fees: bool
    maintain_bnb_balance_usd: Decimal
    vip_tier_target: str


class CapitalProfileResponse(BaseModel):
    current_equity: Decimal
    active_profile: CapitalProfileRead
    fee_strategy: FeeStrategyRead
    enforcement_notes: list[str]
