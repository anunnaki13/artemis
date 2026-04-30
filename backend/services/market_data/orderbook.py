from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


DEPTH_WINDOW_RATIO = Decimal("0.005")


@dataclass(frozen=True)
class OrderBookLevel:
    price: Decimal
    quantity: Decimal


@dataclass(frozen=True)
class OrderBookMetrics:
    spread: Decimal | None
    spread_bps: Decimal | None
    mid_price: Decimal | None
    bid_depth_notional_0p5pct: Decimal
    ask_depth_notional_0p5pct: Decimal
    imbalance_ratio_0p5pct: Decimal | None
    best_bid: Decimal | None
    best_ask: Decimal | None
    last_update_id: int | None
    updated_at: datetime | None


@dataclass
class OrderBookState:
    symbol: str
    bids: dict[Decimal, Decimal] = field(default_factory=dict)
    asks: dict[Decimal, Decimal] = field(default_factory=dict)
    last_update_id: int | None = None
    updated_at: datetime | None = None

    def load_snapshot(
        self,
        bids: list[list[str]],
        asks: list[list[str]],
        last_update_id: int,
        updated_at: datetime,
    ) -> None:
        self.bids = _normalize_side(bids)
        self.asks = _normalize_side(asks)
        self.last_update_id = last_update_id
        self.updated_at = updated_at

    def apply_depth_update(
        self,
        first_update_id: int,
        final_update_id: int,
        bids: list[list[str]],
        asks: list[list[str]],
        updated_at: datetime,
    ) -> bool:
        if self.last_update_id is None:
            return False
        if final_update_id <= self.last_update_id:
            return False
        if first_update_id > self.last_update_id + 1:
            raise ValueError("depth update gap detected")

        _apply_side_updates(self.bids, bids)
        _apply_side_updates(self.asks, asks)
        self.last_update_id = final_update_id
        self.updated_at = updated_at
        return True

    def top_bids(self, limit: int) -> list[OrderBookLevel]:
        return [
            OrderBookLevel(price=price, quantity=quantity)
            for price, quantity in sorted(self.bids.items(), key=lambda item: item[0], reverse=True)[:limit]
        ]

    def top_asks(self, limit: int) -> list[OrderBookLevel]:
        return [
            OrderBookLevel(price=price, quantity=quantity)
            for price, quantity in sorted(self.asks.items(), key=lambda item: item[0])[:limit]
        ]

    def metrics(self) -> OrderBookMetrics:
        best_bid = max(self.bids) if self.bids else None
        best_ask = min(self.asks) if self.asks else None
        if best_bid is None or best_ask is None:
            return OrderBookMetrics(
                spread=None,
                spread_bps=None,
                mid_price=None,
                bid_depth_notional_0p5pct=Decimal("0"),
                ask_depth_notional_0p5pct=Decimal("0"),
                imbalance_ratio_0p5pct=None,
                best_bid=best_bid,
                best_ask=best_ask,
                last_update_id=self.last_update_id,
                updated_at=self.updated_at,
            )

        spread = best_ask - best_bid
        mid_price = (best_bid + best_ask) / Decimal("2")
        spread_bps = (spread / mid_price) * Decimal("10000") if mid_price != 0 else None
        bid_cutoff = mid_price * (Decimal("1") - DEPTH_WINDOW_RATIO)
        ask_cutoff = mid_price * (Decimal("1") + DEPTH_WINDOW_RATIO)
        bid_depth = sum(
            (price * quantity for price, quantity in self.bids.items() if price >= bid_cutoff),
            start=Decimal("0"),
        )
        ask_depth = sum(
            (price * quantity for price, quantity in self.asks.items() if price <= ask_cutoff),
            start=Decimal("0"),
        )
        total_depth = bid_depth + ask_depth
        imbalance_ratio = ((bid_depth - ask_depth) / total_depth) if total_depth != Decimal("0") else None
        return OrderBookMetrics(
            spread=spread,
            spread_bps=spread_bps,
            mid_price=mid_price,
            bid_depth_notional_0p5pct=bid_depth,
            ask_depth_notional_0p5pct=ask_depth,
            imbalance_ratio_0p5pct=imbalance_ratio,
            best_bid=best_bid,
            best_ask=best_ask,
            last_update_id=self.last_update_id,
            updated_at=self.updated_at,
        )


def _normalize_side(levels: list[list[str]]) -> dict[Decimal, Decimal]:
    side: dict[Decimal, Decimal] = {}
    _apply_side_updates(side, levels)
    return side


def _apply_side_updates(side: dict[Decimal, Decimal], levels: list[list[str]]) -> None:
    for raw_price, raw_quantity in levels:
        price = Decimal(str(raw_price))
        quantity = Decimal(str(raw_quantity))
        if quantity == 0:
            side.pop(price, None)
        else:
            side[price] = quantity


def metrics_to_payload(metrics: OrderBookMetrics) -> dict[str, str | int | None]:
    return {
        "spread": str(metrics.spread) if metrics.spread is not None else None,
        "spread_bps": str(metrics.spread_bps) if metrics.spread_bps is not None else None,
        "mid_price": str(metrics.mid_price) if metrics.mid_price is not None else None,
        "bid_depth_notional_0p5pct": str(metrics.bid_depth_notional_0p5pct),
        "ask_depth_notional_0p5pct": str(metrics.ask_depth_notional_0p5pct),
        "imbalance_ratio_0p5pct": (
            str(metrics.imbalance_ratio_0p5pct) if metrics.imbalance_ratio_0p5pct is not None else None
        ),
        "best_bid": str(metrics.best_bid) if metrics.best_bid is not None else None,
        "best_ask": str(metrics.best_ask) if metrics.best_ask is not None else None,
        "last_update_id": metrics.last_update_id,
    }


def levels_to_payload(levels: list[OrderBookLevel]) -> list[dict[str, str]]:
    return [{"price": str(level.price), "quantity": str(level.quantity)} for level in levels]


def levels_from_payload(payload: list[dict[str, Any]]) -> list[OrderBookLevel]:
    return [
        OrderBookLevel(price=Decimal(str(level["price"])), quantity=Decimal(str(level["quantity"])))
        for level in payload
    ]


def metrics_from_payload(payload: dict[str, Any], updated_at: datetime) -> OrderBookMetrics | None:
    raw_metrics = payload.get("metrics")
    if not isinstance(raw_metrics, dict):
        return None
    return OrderBookMetrics(
        spread=_decimal_from_payload(raw_metrics.get("spread")),
        spread_bps=_decimal_from_payload(raw_metrics.get("spread_bps")),
        mid_price=_decimal_from_payload(raw_metrics.get("mid_price")),
        bid_depth_notional_0p5pct=_decimal_from_payload(raw_metrics.get("bid_depth_notional_0p5pct"))
        or Decimal("0"),
        ask_depth_notional_0p5pct=_decimal_from_payload(raw_metrics.get("ask_depth_notional_0p5pct"))
        or Decimal("0"),
        imbalance_ratio_0p5pct=_decimal_from_payload(raw_metrics.get("imbalance_ratio_0p5pct")),
        best_bid=_decimal_from_payload(raw_metrics.get("best_bid")),
        best_ask=_decimal_from_payload(raw_metrics.get("best_ask")),
        last_update_id=_int_from_payload(raw_metrics.get("last_update_id")),
        updated_at=updated_at,
    )


def _decimal_from_payload(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _int_from_payload(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
