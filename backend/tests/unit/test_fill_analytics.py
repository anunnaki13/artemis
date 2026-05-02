from datetime import datetime, timezone
from decimal import Decimal

from app.models import ExecutionIntent, SpotExecutionFill
from services.execution.fill_analytics import (
    summarize_fill_chains,
    summarize_fill_quality,
    summarize_intent_lineage_outcomes,
    summarize_intent_outcomes,
    summarize_strategy_quality,
)


def build_fill(
    *,
    fill_id: int,
    client_order_id: str,
    symbol: str,
    side: str,
    quantity: str,
    quote_quantity: str,
    price: str,
    realized_pnl_usd: str,
    post_fill_net_quantity: str,
    filled_at_second: int,
    execution_intent_id: int | None = None,
    source_strategy: str | None = None,
) -> SpotExecutionFill:
    return SpotExecutionFill(
        id=fill_id,
        filled_at=datetime(2026, 5, 1, 0, 0, filled_at_second, tzinfo=timezone.utc),
        symbol=symbol,
        side=side,
        execution_intent_id=execution_intent_id,
        source_strategy=source_strategy,
        client_order_id=client_order_id,
        venue_order_id=f"venue-{client_order_id}",
        trade_id=fill_id,
        quantity=Decimal(quantity),
        quote_quantity=Decimal(quote_quantity),
        price=Decimal(price),
        realized_pnl_usd=Decimal(realized_pnl_usd),
        post_fill_net_quantity=Decimal(post_fill_net_quantity),
        post_fill_average_entry_price=Decimal(price) if Decimal(post_fill_net_quantity) > 0 else None,
        source_event="executionReport",
    )


def build_intent(
    *,
    intent_id: int,
    symbol: str,
    side: str,
    source_strategy: str,
    status: str,
    requested_notional: str,
    approved_notional: str,
    entry_price: str,
    created_at_second: int,
) -> ExecutionIntent:
    return ExecutionIntent(
        id=intent_id,
        symbol=symbol,
        side=side,
        status=status,
        source_strategy=source_strategy,
        requested_notional=Decimal(requested_notional),
        approved_notional=Decimal(approved_notional),
        entry_price=Decimal(entry_price),
        created_at=datetime(2026, 5, 1, 0, 0, created_at_second, tzinfo=timezone.utc),
        owner_user_id="user-1",
        signal_payload={"symbol": symbol, "side": side, "source": source_strategy, "conviction": 0.8, "regime": "micro"},
        risk_payload={"allowed": True, "reasons": [], "profile_name": "paper", "recommended_max_notional": approved_notional},
        notes=None,
    )


def test_summarize_fill_chains_groups_by_order_identifier() -> None:
    fills = [
        build_fill(
            fill_id=1,
            client_order_id="client-a",
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.10",
            quote_quantity="6500",
            price="65000",
            realized_pnl_usd="0",
            post_fill_net_quantity="0.10",
            filled_at_second=1,
            execution_intent_id=11,
            source_strategy="orderbook_imbalance",
        ),
        build_fill(
            fill_id=2,
            client_order_id="client-a",
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.05",
            quote_quantity="3250",
            price="65000",
            realized_pnl_usd="0",
            post_fill_net_quantity="0.15",
            filled_at_second=2,
            execution_intent_id=11,
            source_strategy="orderbook_imbalance",
        ),
        build_fill(
            fill_id=3,
            client_order_id="client-b",
            symbol="BTCUSDT",
            side="SELL",
            quantity="0.05",
            quote_quantity="3300",
            price="66000",
            realized_pnl_usd="50",
            post_fill_net_quantity="0.10",
            filled_at_second=3,
            execution_intent_id=12,
            source_strategy="mean_reversion",
        ),
    ]

    chains = summarize_fill_chains(fills)

    assert len(chains) == 2
    latest = chains[0]
    assert latest.client_order_id == "client-b"
    assert latest.source_strategy == "mean_reversion"
    assert latest.realized_pnl_usd == Decimal("50")
    earlier = chains[1]
    assert earlier.client_order_id == "client-a"
    assert earlier.execution_intent_id == 11
    assert earlier.fills_count == 2
    assert earlier.total_quantity == Decimal("0.15")
    assert earlier.total_quote_quantity == Decimal("9750")
    assert earlier.average_price == Decimal("65000")


def test_summarize_fill_quality_computes_win_rate_and_notional() -> None:
    fills = [
        build_fill(
            fill_id=1,
            client_order_id="client-a",
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.10",
            quote_quantity="6500",
            price="65000",
            realized_pnl_usd="0",
            post_fill_net_quantity="0.10",
            filled_at_second=1,
            execution_intent_id=11,
            source_strategy="orderbook_imbalance",
        ),
        build_fill(
            fill_id=2,
            client_order_id="client-b",
            symbol="BTCUSDT",
            side="SELL",
            quantity="0.05",
            quote_quantity="3300",
            price="66000",
            realized_pnl_usd="50",
            post_fill_net_quantity="0.05",
            filled_at_second=2,
            execution_intent_id=12,
            source_strategy="mean_reversion",
        ),
        build_fill(
            fill_id=3,
            client_order_id="client-c",
            symbol="ETHUSDT",
            side="SELL",
            quantity="1.0",
            quote_quantity="3000",
            price="3000",
            realized_pnl_usd="-25",
            post_fill_net_quantity="0",
            filled_at_second=3,
            execution_intent_id=13,
            source_strategy="mean_reversion",
        ),
    ]

    summary = summarize_fill_quality(fills)

    assert summary.fills_count == 3
    assert summary.chains_count == 3
    assert summary.traded_symbols_count == 2
    assert summary.gross_notional_usd == Decimal("12800")
    assert summary.gross_realized_pnl_usd == Decimal("25")
    assert summary.winning_fills_count == 1
    assert summary.losing_fills_count == 1
    assert summary.flat_fills_count == 1
    assert summary.win_rate == Decimal("0.5")


def test_summarize_strategy_quality_groups_by_source_strategy() -> None:
    fills = [
        build_fill(
            fill_id=1,
            client_order_id="client-a",
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.10",
            quote_quantity="6500",
            price="65000",
            realized_pnl_usd="0",
            post_fill_net_quantity="0.10",
            filled_at_second=1,
            source_strategy="orderbook_imbalance",
        ),
        build_fill(
            fill_id=2,
            client_order_id="client-b",
            symbol="BTCUSDT",
            side="SELL",
            quantity="0.05",
            quote_quantity="3300",
            price="66000",
            realized_pnl_usd="50",
            post_fill_net_quantity="0.05",
            filled_at_second=2,
            source_strategy="mean_reversion",
        ),
        build_fill(
            fill_id=3,
            client_order_id="client-c",
            symbol="ETHUSDT",
            side="SELL",
            quantity="1.0",
            quote_quantity="3000",
            price="3000",
            realized_pnl_usd="-25",
            post_fill_net_quantity="0",
            filled_at_second=3,
            source_strategy="mean_reversion",
        ),
    ]

    strategy_rows = summarize_strategy_quality(fills)

    assert len(strategy_rows) == 2
    assert strategy_rows[0].source_strategy == "mean_reversion"
    assert strategy_rows[0].gross_realized_pnl_usd == Decimal("25")
    assert strategy_rows[1].source_strategy == "orderbook_imbalance"


def test_summarize_intent_outcomes_links_realized_result_to_signal_intent() -> None:
    intents = [
        build_intent(
            intent_id=11,
            symbol="BTCUSDT",
            side="BUY",
            source_strategy="orderbook_imbalance",
            status="executed",
            requested_notional="1200",
            approved_notional="1000",
            entry_price="65000",
            created_at_second=1,
        ),
        build_intent(
            intent_id=12,
            symbol="ETHUSDT",
            side="SELL",
            source_strategy="mean_reversion",
            status="approved",
            requested_notional="800",
            approved_notional="750",
            entry_price="3000",
            created_at_second=2,
        ),
    ]
    fills = [
        build_fill(
            fill_id=1,
            client_order_id="client-a",
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.01",
            quote_quantity="650",
            price="65000",
            realized_pnl_usd="0",
            post_fill_net_quantity="0.01",
            filled_at_second=3,
            execution_intent_id=11,
            source_strategy="orderbook_imbalance",
        ),
        build_fill(
            fill_id=2,
            client_order_id="client-a",
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.005",
            quote_quantity="330",
            price="66000",
            realized_pnl_usd="12",
            post_fill_net_quantity="0.015",
            filled_at_second=4,
            execution_intent_id=11,
            source_strategy="orderbook_imbalance",
        ),
    ]

    outcomes = summarize_intent_outcomes(intents, fills)

    assert [item.execution_intent_id for item in outcomes] == [12, 11]
    pending = outcomes[0]
    assert pending.fills_count == 0
    assert pending.fill_ratio == Decimal("0")
    assert pending.average_fill_price is None

    executed = outcomes[1]
    assert executed.fills_count == 2
    assert executed.filled_quote_quantity == Decimal("980")
    assert executed.realized_pnl_usd == Decimal("12")
    assert executed.fill_ratio == Decimal("0.98")
    assert executed.average_fill_price == Decimal("65333.33333333333333333333333")
    assert executed.slippage_bps is not None
    assert executed.slippage_bps.quantize(Decimal("0.0001")) == Decimal("51.2821")
    assert executed.adverse_slippage_bps is not None
    assert executed.adverse_slippage_bps.quantize(Decimal("0.0001")) == Decimal("51.2821")
    assert executed.slippage_cost_usd.quantize(Decimal("0.0001")) == Decimal("5.0000")
    assert executed.underfill_notional_usd == Decimal("20")


def test_summarize_intent_lineage_outcomes_rolls_replacements_into_root_chain() -> None:
    original = build_intent(
        intent_id=21,
        symbol="BTCUSDT",
        side="BUY",
        source_strategy="orderbook_imbalance",
        status="cancelled",
        requested_notional="1200",
        approved_notional="1000",
        entry_price="65000",
        created_at_second=1,
    )
    replacement = build_intent(
        intent_id=22,
        symbol="BTCUSDT",
        side="BUY",
        source_strategy="orderbook_imbalance",
        status="executed",
        requested_notional="1200",
        approved_notional="900",
        entry_price="64800",
        created_at_second=2,
    )
    replacement.parent_intent_id = 21

    fills = [
        build_fill(
            fill_id=10,
            client_order_id="client-r1",
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.006",
            quote_quantity="390",
            price="65000",
            realized_pnl_usd="0",
            post_fill_net_quantity="0.006",
            filled_at_second=3,
            execution_intent_id=21,
            source_strategy="orderbook_imbalance",
        ),
        build_fill(
            fill_id=11,
            client_order_id="client-r2",
            symbol="BTCUSDT",
            side="BUY",
            quantity="0.008",
            quote_quantity="520",
            price="65000",
            realized_pnl_usd="14",
            post_fill_net_quantity="0.014",
            filled_at_second=4,
            execution_intent_id=22,
            source_strategy="orderbook_imbalance",
        ),
    ]

    lineages = summarize_intent_lineage_outcomes([original, replacement], fills)

    assert len(lineages) == 1
    lineage = lineages[0]
    assert lineage.root_intent_id == 21
    assert lineage.latest_intent_id == 22
    assert lineage.lineage_size == 2
    assert lineage.lineage_statuses == ["cancelled", "executed"]
    assert lineage.fills_count == 2
    assert lineage.filled_quote_quantity == Decimal("910")
    assert lineage.realized_pnl_usd == Decimal("14")
    assert lineage.fill_ratio.quantize(Decimal("0.0001")) == Decimal("1.0111")
    assert lineage.adverse_slippage_bps is not None
    assert lineage.adverse_slippage_bps.quantize(Decimal("0.0001")) == Decimal("30.8642")
    assert lineage.slippage_cost_usd.quantize(Decimal("0.0001")) == Decimal("1.6000")
    assert lineage.underfill_notional_usd == Decimal("0")
