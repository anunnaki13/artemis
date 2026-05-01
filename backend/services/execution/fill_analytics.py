from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.models import ExecutionIntent, SpotExecutionFill


def order_chain_key(fill: SpotExecutionFill) -> str:
    if fill.client_order_id:
        return f"client:{fill.client_order_id}"
    if fill.venue_order_id:
        return f"venue:{fill.venue_order_id}"
    return f"fill:{fill.id}"


@dataclass(frozen=True)
class FillChainSummary:
    chain_key: str
    symbol: str
    side: str
    execution_intent_id: int | None
    source_strategy: str | None
    client_order_id: str | None
    venue_order_id: str | None
    fills_count: int
    opened_at: datetime
    closed_at: datetime
    total_quantity: Decimal
    total_quote_quantity: Decimal
    average_price: Decimal
    realized_pnl_usd: Decimal
    ending_net_quantity: Decimal
    ending_average_entry_price: Decimal | None


@dataclass(frozen=True)
class FillQualitySummary:
    fills_count: int
    chains_count: int
    traded_symbols_count: int
    gross_notional_usd: Decimal
    gross_realized_pnl_usd: Decimal
    winning_fills_count: int
    losing_fills_count: int
    flat_fills_count: int
    win_rate: Decimal
    average_fill_notional_usd: Decimal
    average_realized_pnl_per_fill_usd: Decimal


@dataclass(frozen=True)
class StrategyQualitySummary:
    source_strategy: str
    fills_count: int
    chains_count: int
    gross_notional_usd: Decimal
    gross_realized_pnl_usd: Decimal
    win_rate: Decimal


@dataclass(frozen=True)
class IntentOutcomeSummary:
    execution_intent_id: int
    symbol: str
    side: str
    source_strategy: str
    intent_status: str
    requested_notional: Decimal
    approved_notional: Decimal
    entry_price: Decimal
    created_at: datetime
    dispatched_at: datetime | None
    executed_at: datetime | None
    fills_count: int
    filled_quantity: Decimal
    filled_quote_quantity: Decimal
    average_fill_price: Decimal | None
    realized_pnl_usd: Decimal
    fill_ratio: Decimal
    slippage_bps: Decimal | None
    last_fill_at: datetime | None


@dataclass(frozen=True)
class IntentLineageOutcomeSummary:
    root_intent_id: int
    latest_intent_id: int
    symbol: str
    side: str
    source_strategy: str
    lineage_size: int
    lineage_statuses: list[str]
    requested_notional: Decimal
    approved_notional: Decimal
    created_at: datetime
    latest_created_at: datetime
    fills_count: int
    filled_quantity: Decimal
    filled_quote_quantity: Decimal
    average_fill_price: Decimal | None
    realized_pnl_usd: Decimal
    fill_ratio: Decimal
    slippage_bps: Decimal | None
    last_fill_at: datetime | None


def summarize_fill_chains(fills: list[SpotExecutionFill]) -> list[FillChainSummary]:
    chains: dict[str, list[SpotExecutionFill]] = {}
    for fill in fills:
        chains.setdefault(order_chain_key(fill), []).append(fill)

    summaries: list[FillChainSummary] = []
    for chain_key, chain_fills in chains.items():
        ordered = sorted(chain_fills, key=lambda item: (item.filled_at, int(item.id)))
        total_quantity = sum((fill.quantity for fill in ordered), Decimal("0"))
        total_quote_quantity = sum((fill.quote_quantity for fill in ordered), Decimal("0"))
        realized_pnl = sum((fill.realized_pnl_usd for fill in ordered), Decimal("0"))
        average_price = (
            total_quote_quantity / total_quantity if total_quantity != Decimal("0") else Decimal("0")
        )
        last_fill = ordered[-1]
        first_fill = ordered[0]
        summaries.append(
            FillChainSummary(
                chain_key=chain_key,
                symbol=first_fill.symbol,
                side=first_fill.side,
                execution_intent_id=first_fill.execution_intent_id,
                source_strategy=first_fill.source_strategy,
                client_order_id=first_fill.client_order_id,
                venue_order_id=first_fill.venue_order_id,
                fills_count=len(ordered),
                opened_at=first_fill.filled_at,
                closed_at=last_fill.filled_at,
                total_quantity=total_quantity,
                total_quote_quantity=total_quote_quantity,
                average_price=average_price,
                realized_pnl_usd=realized_pnl,
                ending_net_quantity=last_fill.post_fill_net_quantity,
                ending_average_entry_price=last_fill.post_fill_average_entry_price,
            )
        )
    return sorted(summaries, key=lambda item: item.closed_at, reverse=True)


def summarize_fill_quality(fills: list[SpotExecutionFill]) -> FillQualitySummary:
    fills_count = len(fills)
    chains = summarize_fill_chains(fills)
    gross_notional = sum((fill.quote_quantity for fill in fills), Decimal("0"))
    gross_realized_pnl = sum((fill.realized_pnl_usd for fill in fills), Decimal("0"))
    winning_fills = sum(1 for fill in fills if fill.realized_pnl_usd > Decimal("0"))
    losing_fills = sum(1 for fill in fills if fill.realized_pnl_usd < Decimal("0"))
    flat_fills = fills_count - winning_fills - losing_fills
    average_fill_notional = gross_notional / fills_count if fills_count > 0 else Decimal("0")
    average_realized_pnl = gross_realized_pnl / fills_count if fills_count > 0 else Decimal("0")
    denominator = winning_fills + losing_fills
    win_rate = Decimal(winning_fills) / Decimal(denominator) if denominator > 0 else Decimal("0")
    traded_symbols_count = len({fill.symbol for fill in fills})
    return FillQualitySummary(
        fills_count=fills_count,
        chains_count=len(chains),
        traded_symbols_count=traded_symbols_count,
        gross_notional_usd=gross_notional,
        gross_realized_pnl_usd=gross_realized_pnl,
        winning_fills_count=winning_fills,
        losing_fills_count=losing_fills,
        flat_fills_count=flat_fills,
        win_rate=win_rate,
        average_fill_notional_usd=average_fill_notional,
        average_realized_pnl_per_fill_usd=average_realized_pnl,
    )


def summarize_strategy_quality(fills: list[SpotExecutionFill]) -> list[StrategyQualitySummary]:
    strategies: dict[str, list[SpotExecutionFill]] = {}
    for fill in fills:
        key = fill.source_strategy or "unattributed"
        strategies.setdefault(key, []).append(fill)

    summaries: list[StrategyQualitySummary] = []
    for strategy, strategy_fills in strategies.items():
        chains = summarize_fill_chains(strategy_fills)
        gross_notional = sum((fill.quote_quantity for fill in strategy_fills), Decimal("0"))
        gross_realized = sum((fill.realized_pnl_usd for fill in strategy_fills), Decimal("0"))
        winning_fills = sum(1 for fill in strategy_fills if fill.realized_pnl_usd > Decimal("0"))
        losing_fills = sum(1 for fill in strategy_fills if fill.realized_pnl_usd < Decimal("0"))
        denominator = winning_fills + losing_fills
        win_rate = Decimal(winning_fills) / Decimal(denominator) if denominator > 0 else Decimal("0")
        summaries.append(
            StrategyQualitySummary(
                source_strategy=strategy,
                fills_count=len(strategy_fills),
                chains_count=len(chains),
                gross_notional_usd=gross_notional,
                gross_realized_pnl_usd=gross_realized,
                win_rate=win_rate,
            )
        )
    return sorted(summaries, key=lambda item: (item.gross_realized_pnl_usd, item.gross_notional_usd), reverse=True)


def summarize_intent_outcomes(
    intents: list[ExecutionIntent],
    fills: list[SpotExecutionFill],
) -> list[IntentOutcomeSummary]:
    fills_by_intent: dict[int, list[SpotExecutionFill]] = {}
    for fill in fills:
        if fill.execution_intent_id is None:
            continue
        fills_by_intent.setdefault(int(fill.execution_intent_id), []).append(fill)

    summaries: list[IntentOutcomeSummary] = []
    for intent in intents:
        if intent.id is None:
            continue
        ordered_fills = sorted(
            fills_by_intent.get(int(intent.id), []),
            key=lambda item: (item.filled_at, int(item.id)),
        )
        filled_quantity = sum((fill.quantity for fill in ordered_fills), Decimal("0"))
        filled_quote_quantity = sum((fill.quote_quantity for fill in ordered_fills), Decimal("0"))
        realized_pnl = sum((fill.realized_pnl_usd for fill in ordered_fills), Decimal("0"))
        average_fill_price = (
            filled_quote_quantity / filled_quantity if filled_quantity != Decimal("0") else None
        )
        fill_ratio = (
            filled_quote_quantity / intent.approved_notional
            if intent.approved_notional != Decimal("0")
            else Decimal("0")
        )
        slippage_bps: Decimal | None = None
        if average_fill_price is not None and intent.entry_price != Decimal("0"):
            direction = Decimal("1") if intent.side.upper() == "BUY" else Decimal("-1")
            slippage_bps = ((average_fill_price - intent.entry_price) / intent.entry_price) * Decimal("10000")
            slippage_bps *= direction

        summaries.append(
            IntentOutcomeSummary(
                execution_intent_id=int(intent.id),
                symbol=intent.symbol,
                side=intent.side,
                source_strategy=intent.source_strategy,
                intent_status=intent.status,
                requested_notional=intent.requested_notional,
                approved_notional=intent.approved_notional,
                entry_price=intent.entry_price,
                created_at=intent.created_at,
                dispatched_at=intent.dispatched_at,
                executed_at=intent.executed_at,
                fills_count=len(ordered_fills),
                filled_quantity=filled_quantity,
                filled_quote_quantity=filled_quote_quantity,
                average_fill_price=average_fill_price,
                realized_pnl_usd=realized_pnl,
                fill_ratio=fill_ratio,
                slippage_bps=slippage_bps,
                last_fill_at=ordered_fills[-1].filled_at if ordered_fills else None,
            )
        )
    return sorted(summaries, key=lambda item: item.created_at, reverse=True)


def summarize_intent_lineage_outcomes(
    intents: list[ExecutionIntent],
    fills: list[SpotExecutionFill],
) -> list[IntentLineageOutcomeSummary]:
    intents_by_id = {int(intent.id): intent for intent in intents if intent.id is not None}

    def root_intent_id(intent: ExecutionIntent) -> int:
        if intent.id is None:
            raise ValueError("intent id is required")
        root_id = int(intent.id)
        current = intent
        seen: set[int] = set()
        while current.parent_intent_id is not None and int(current.parent_intent_id) not in seen:
            parent_id = int(current.parent_intent_id)
            seen.add(parent_id)
            parent = intents_by_id.get(parent_id)
            if parent is None:
                root_id = parent_id
                break
            root_id = parent_id
            current = parent
        return root_id

    lineage_map: dict[int, list[ExecutionIntent]] = {}
    for intent in intents:
        if intent.id is None:
            continue
        lineage_map.setdefault(root_intent_id(intent), []).append(intent)

    summaries: list[IntentLineageOutcomeSummary] = []
    for root_id, lineage_intents in lineage_map.items():
        ordered_intents = sorted(lineage_intents, key=lambda item: (item.created_at, int(item.id)))
        latest_intent = ordered_intents[-1]
        lineage_intent_ids = {int(item.id) for item in ordered_intents if item.id is not None}
        lineage_fills = [
            fill
            for fill in fills
            if fill.execution_intent_id is not None
            and int(fill.execution_intent_id) in lineage_intent_ids
        ]
        lineage_intent_outcomes = summarize_intent_outcomes(ordered_intents, lineage_fills)
        latest_outcome = next(
            item for item in lineage_intent_outcomes if item.execution_intent_id == int(latest_intent.id)
        )
        summaries.append(
            IntentLineageOutcomeSummary(
                root_intent_id=root_id,
                latest_intent_id=int(latest_intent.id),
                symbol=latest_intent.symbol,
                side=latest_intent.side,
                source_strategy=latest_intent.source_strategy,
                lineage_size=len(ordered_intents),
                lineage_statuses=[item.status for item in ordered_intents],
                requested_notional=latest_intent.requested_notional,
                approved_notional=latest_intent.approved_notional,
                created_at=ordered_intents[0].created_at,
                latest_created_at=latest_intent.created_at,
                fills_count=sum(item.fills_count for item in lineage_intent_outcomes),
                filled_quantity=sum((fill.quantity for fill in lineage_fills), Decimal("0")),
                filled_quote_quantity=sum((fill.quote_quantity for fill in lineage_fills), Decimal("0")),
                average_fill_price=latest_outcome.average_fill_price,
                realized_pnl_usd=sum((fill.realized_pnl_usd for fill in lineage_fills), Decimal("0")),
                fill_ratio=(
                    sum((fill.quote_quantity for fill in lineage_fills), Decimal("0")) / latest_intent.approved_notional
                    if latest_intent.approved_notional != Decimal("0")
                    else Decimal("0")
                ),
                slippage_bps=latest_outcome.slippage_bps,
                last_fill_at=max((fill.filled_at for fill in lineage_fills), default=None),
            )
        )
    return sorted(summaries, key=lambda item: item.latest_created_at, reverse=True)
