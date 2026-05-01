from datetime import datetime, timezone
from decimal import Decimal

from app.models import MarketSnapshot, SpotExecutionFill, SpotOrderFillState, SpotSymbolPosition, Symbol
from services.execution.account_state import SpotAccountStateService


class FakePositionSession:
    def __init__(self) -> None:
        self.market_snapshots: dict[str, MarketSnapshot] = {}
        self.execution_fills: list[SpotExecutionFill] = []
        self.fill_states: dict[str, SpotOrderFillState] = {}
        self.positions: dict[str, SpotSymbolPosition] = {}
        self.symbols: dict[str, Symbol] = {}

    async def get(self, model: type[object], key: str) -> object | None:
        if model is SpotOrderFillState:
            return self.fill_states.get(key)
        if model is SpotSymbolPosition:
            return self.positions.get(key)
        if model is Symbol:
            return self.symbols.get(key)
        return None

    async def scalar(self, _query: object) -> object | None:
        query_text = str(_query)
        if "spot_order_fill_states" in query_text:
            return next(iter(self.fill_states.values()), None) if self.fill_states else None
        if "market_snapshots" in query_text:
            return next(iter(self.market_snapshots.values()), None) if self.market_snapshots else None
        return None

    def add(self, obj: object) -> None:
        if isinstance(obj, SpotOrderFillState):
            self.fill_states[obj.order_key] = obj
        if isinstance(obj, SpotExecutionFill):
            self.execution_fills.append(obj)
        if isinstance(obj, SpotSymbolPosition):
            self.positions[obj.symbol] = obj

    async def flush(self) -> None:
        return None


async def test_position_state_service_applies_buy_fill() -> None:
    session = FakePositionSession()
    session.symbols["BTCUSDT"] = Symbol(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        market_type="spot",
        status="TRADING",
        min_notional=None,
        tick_size=None,
        step_size=None,
        is_enabled=True,
        updated_at=datetime.now(tz=timezone.utc),
    )
    service = SpotAccountStateService()
    session.market_snapshots["BTCUSDT"] = MarketSnapshot(
        symbol="BTCUSDT",
        timestamp=datetime.now(tz=timezone.utc),
        bid_price=None,
        ask_price=None,
        last_price=Decimal("65000"),
        funding_rate=None,
        open_interest=None,
        payload=None,
    )

    position = await service.apply_execution_fill(
        session,  # type: ignore[arg-type]
        symbol="BTCUSDT",
        side="BUY",
        client_order_id="client-1",
        venue_order_id="venue-1",
        cumulative_quantity=Decimal("0.1"),
        cumulative_quote_quantity=Decimal("6500"),
    )

    assert position is not None
    assert position.net_quantity == Decimal("0.1")
    assert position.average_entry_price == Decimal("65000")
    assert position.quote_exposure_usd == Decimal("6500")
    assert position.last_mark_price == Decimal("65000")
    assert position.market_value_usd == Decimal("6500.0")
    assert position.unrealized_pnl_usd == Decimal("0.0")
    assert len(session.execution_fills) == 1
    assert session.execution_fills[0].realized_pnl_usd == Decimal("0")


async def test_position_state_service_reduces_position_on_sell_fill() -> None:
    session = FakePositionSession()
    session.positions["BTCUSDT"] = SpotSymbolPosition(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        net_quantity=Decimal("0.2"),
        average_entry_price=Decimal("60000"),
        last_mark_price=None,
        quote_exposure_usd=Decimal("12000"),
        market_value_usd=None,
        realized_notional=Decimal("0"),
        realized_pnl_usd=Decimal("0"),
        unrealized_pnl_usd=None,
        updated_at=datetime.now(tz=timezone.utc),
        source_event="executionReport",
    )
    service = SpotAccountStateService()
    session.market_snapshots["BTCUSDT"] = MarketSnapshot(
        symbol="BTCUSDT",
        timestamp=datetime.now(tz=timezone.utc),
        bid_price=None,
        ask_price=None,
        last_price=Decimal("65000"),
        funding_rate=None,
        open_interest=None,
        payload=None,
    )

    position = await service.apply_execution_fill(
        session,  # type: ignore[arg-type]
        symbol="BTCUSDT",
        side="SELL",
        client_order_id="client-2",
        venue_order_id="venue-2",
        cumulative_quantity=Decimal("0.05"),
        cumulative_quote_quantity=Decimal("3250"),
    )

    assert position is not None
    assert position.net_quantity == Decimal("0.15")
    assert position.average_entry_price == Decimal("60000")
    assert position.quote_exposure_usd == Decimal("9000")
    assert position.realized_notional == Decimal("3250")
    assert position.realized_pnl_usd == Decimal("250.00")
    assert position.last_mark_price == Decimal("65000")
    assert position.market_value_usd == Decimal("9750.00")
    assert position.unrealized_pnl_usd == Decimal("750.00")
    assert len(session.execution_fills) == 1
    assert session.execution_fills[0].realized_pnl_usd == Decimal("250.00")


async def test_position_state_service_ignores_duplicate_partial_fill_event() -> None:
    session = FakePositionSession()
    session.symbols["BTCUSDT"] = Symbol(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        market_type="spot",
        status="TRADING",
        min_notional=None,
        tick_size=None,
        step_size=None,
        is_enabled=True,
        updated_at=datetime.now(tz=timezone.utc),
    )
    service = SpotAccountStateService()
    session.market_snapshots["BTCUSDT"] = MarketSnapshot(
        symbol="BTCUSDT",
        timestamp=datetime.now(tz=timezone.utc),
        bid_price=None,
        ask_price=None,
        last_price=Decimal("65000"),
        funding_rate=None,
        open_interest=None,
        payload=None,
    )

    first = await service.apply_execution_fill(
        session,  # type: ignore[arg-type]
        symbol="BTCUSDT",
        side="BUY",
        client_order_id="client-3",
        venue_order_id="venue-3",
        cumulative_quantity=Decimal("0.10"),
        cumulative_quote_quantity=Decimal("6500"),
        last_trade_id=1001,
    )
    duplicate = await service.apply_execution_fill(
        session,  # type: ignore[arg-type]
        symbol="BTCUSDT",
        side="BUY",
        client_order_id="client-3",
        venue_order_id="venue-3",
        cumulative_quantity=Decimal("0.10"),
        cumulative_quote_quantity=Decimal("6500"),
        last_trade_id=1001,
    )
    second = await service.apply_execution_fill(
        session,  # type: ignore[arg-type]
        symbol="BTCUSDT",
        side="BUY",
        client_order_id="client-3",
        venue_order_id="venue-3",
        cumulative_quantity=Decimal("0.15"),
        cumulative_quote_quantity=Decimal("9750"),
        last_trade_id=1002,
    )

    assert first is not None
    assert duplicate is None
    assert second is not None
    assert session.positions["BTCUSDT"].net_quantity == Decimal("0.15")
    assert session.positions["BTCUSDT"].average_entry_price == Decimal("65000")
    assert session.positions["BTCUSDT"].quote_exposure_usd == Decimal("9750")
    assert session.positions["BTCUSDT"].unrealized_pnl_usd == Decimal("0.00")
    assert len(session.execution_fills) == 2
