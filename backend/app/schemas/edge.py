from decimal import Decimal

from pydantic import BaseModel


class UniverseCandidateRead(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    quote_volume: Decimal
    price_change_pct: Decimal


class UniverseRefreshResponse(BaseModel):
    candidates: list[UniverseCandidateRead]
    candidate_count: int
    rejected_count: int
    min_quote_volume_usd: Decimal
    max_quote_volume_usd: Decimal
