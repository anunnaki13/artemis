from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from strategies.base import DataRequirements, Signal, Strategy
from services.market_data.orderbook import OrderBookMetrics


@dataclass(frozen=True)
class OrderBookImbalanceSnapshot:
    symbol: str
    timestamp: datetime
    metrics: OrderBookMetrics


@dataclass(frozen=True)
class OrderBookImbalanceDiagnostics:
    sample_size: int
    latest_timestamp: datetime | None
    latest_imbalance_ratio: Decimal | None
    average_imbalance_ratio: Decimal | None
    latest_spread_bps: Decimal | None
    bid_depth_notional_0p5pct: Decimal
    ask_depth_notional_0p5pct: Decimal
    persistence_ratio_observed: Decimal


class OrderBookImbalanceStrategy(Strategy):
    name = "orderbook_imbalance"
    version = "0.1.0"
    parameter_schema = {
        "lookback": {"type": "integer", "default": 20},
        "min_abs_imbalance": {"type": "number", "default": 0.12},
        "max_spread_bps": {"type": "number", "default": 8},
        "min_depth_notional_usd": {"type": "number", "default": 10000},
        "persistence_ratio": {"type": "number", "default": 0.60},
    }

    async def generate_signal(
        self,
        market_data: list[OrderBookImbalanceSnapshot],
        params: dict[str, Decimal | int],
    ) -> Signal | None:
        if len(market_data) < 3:
            return None

        diagnostics = self.diagnostics(market_data, params)
        latest = market_data[-1]
        latest_imbalance = diagnostics.latest_imbalance_ratio
        average_imbalance = diagnostics.average_imbalance_ratio

        if (
            latest_imbalance is None
            or average_imbalance is None
            or diagnostics.latest_spread_bps is None
            or diagnostics.bid_depth_notional_0p5pct < Decimal(str(params["min_depth_notional_usd"]))
            or diagnostics.ask_depth_notional_0p5pct < Decimal(str(params["min_depth_notional_usd"]))
            or diagnostics.latest_spread_bps > Decimal(str(params["max_spread_bps"]))
            or diagnostics.persistence_ratio_observed < Decimal(str(params["persistence_ratio"]))
        ):
            return None

        threshold = Decimal(str(params["min_abs_imbalance"]))
        side: Literal["long", "short"] | None = None
        if latest_imbalance >= threshold and average_imbalance > 0:
            side = "long"
        elif latest_imbalance <= -threshold and average_imbalance < 0:
            side = "short"
        if side is None:
            return None

        conviction = min(float(abs(latest_imbalance) * Decimal("2")), 1.0)
        metadata = {
            "latest_imbalance_ratio": str(latest_imbalance),
            "average_imbalance_ratio": str(average_imbalance),
            "latest_spread_bps": str(diagnostics.latest_spread_bps),
            "persistence_ratio_observed": str(diagnostics.persistence_ratio_observed),
        }
        return Signal(
            symbol=latest.symbol,
            side=side,
            conviction=conviction,
            source=self.name,
            regime="microstructure",
            metadata=metadata,
        )

    def required_data(self) -> DataRequirements:
        return DataRequirements(timeframes=[], lookback=20, needs_orderbook=True, needs_funding=False)

    def diagnostics(
        self,
        market_data: list[OrderBookImbalanceSnapshot],
        params: dict[str, Decimal | int],
    ) -> OrderBookImbalanceDiagnostics:
        lookback = int(params["lookback"])
        points = market_data[-lookback:]
        ratios = [point.metrics.imbalance_ratio_0p5pct for point in points if point.metrics.imbalance_ratio_0p5pct is not None]
        latest = points[-1]
        latest_ratio = latest.metrics.imbalance_ratio_0p5pct
        average_ratio = (sum(ratios, start=Decimal("0")) / Decimal(len(ratios))) if ratios else None

        sign_matches = Decimal("0")
        if latest_ratio is not None and ratios:
            sign_matches = Decimal(
                sum(1 for ratio in ratios if ratio is not None and (ratio >= 0) == (latest_ratio >= 0))
            ) / Decimal(len(ratios))

        return OrderBookImbalanceDiagnostics(
            sample_size=len(points),
            latest_timestamp=latest.timestamp,
            latest_imbalance_ratio=latest_ratio,
            average_imbalance_ratio=average_ratio,
            latest_spread_bps=latest.metrics.spread_bps,
            bid_depth_notional_0p5pct=latest.metrics.bid_depth_notional_0p5pct,
            ask_depth_notional_0p5pct=latest.metrics.ask_depth_notional_0p5pct,
            persistence_ratio_observed=sign_matches,
        )
