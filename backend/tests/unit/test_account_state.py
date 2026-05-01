from datetime import datetime, timezone
from decimal import Decimal

from app.models import MarketSnapshot, SpotAccountBalance, SpotExecutionFill, SpotSymbolPosition, Symbol
from services.execution.account_state import SpotAccountStateService


class FakeScalarSession:
    def __init__(self) -> None:
        self.balances: dict[str, SpotAccountBalance] = {}
        self.market_snapshots: dict[str, MarketSnapshot] = {}
        self.positions: dict[str, SpotSymbolPosition] = {}
        self.fills: list[SpotExecutionFill] = []
        self.symbols: dict[str, Symbol] = {}

    async def scalar(self, query: object) -> MarketSnapshot | None:
        query_text = str(query)
        if "market_snapshots" in query_text:
            return next(iter(self.market_snapshots.values()), None)
        return None

    async def get(self, model: type[object], key: str) -> object | None:
        if model is SpotAccountBalance:
            return self.balances.get(key)
        if model is SpotSymbolPosition:
            return self.positions.get(key)
        if model is Symbol:
            return self.symbols.get(key)
        return None

    async def execute(self, _statement: object) -> None:
        return None

    def add(self, obj: object) -> None:
        if isinstance(obj, SpotAccountBalance):
            self.balances[obj.asset] = obj
        if isinstance(obj, SpotSymbolPosition):
            self.positions[obj.symbol] = obj
        if isinstance(obj, SpotExecutionFill):
            self.fills.append(obj)

    async def flush(self) -> None:
        return None


async def test_account_state_service_applies_balance_delta() -> None:
    session = FakeScalarSession()
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
    service = SpotAccountStateService()

    balance = await service.apply_balance_delta(
        session,  # type: ignore[arg-type]
        asset="BTC",
        delta=Decimal("0.25"),
    )

    assert balance.asset == "BTC"
    assert balance.free == Decimal("0.25")
    assert balance.total == Decimal("0.25")
    assert balance.total_value_usd == Decimal("16250.00")


async def test_account_state_service_applies_outbound_account_position() -> None:
    session = FakeScalarSession()
    service = SpotAccountStateService()

    balances = await service.apply_outbound_account_position(
        session,  # type: ignore[arg-type]
        [
            {"a": "USDT", "f": "100.5", "l": "5.0"},
            {"a": "BNB", "f": "1.0", "l": "0.2"},
        ],
    )

    assert len(balances) == 2
    assert session.balances["USDT"].total == Decimal("105.5")
    assert session.balances["USDT"].total_value_usd == Decimal("105.5")
    assert session.balances["BNB"].total == Decimal("1.2")


async def test_account_state_service_refreshes_position_mark_and_unrealized_pnl() -> None:
    session = FakeScalarSession()
    session.market_snapshots["BTCUSDT"] = MarketSnapshot(
        symbol="BTCUSDT",
        timestamp=datetime.now(tz=timezone.utc),
        bid_price=Decimal("65990"),
        ask_price=Decimal("66010"),
        last_price=Decimal("66000"),
        funding_rate=None,
        open_interest=None,
        payload=None,
    )
    position = SpotSymbolPosition(
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        net_quantity=Decimal("0.2"),
        average_entry_price=Decimal("65000"),
        last_mark_price=None,
        quote_exposure_usd=Decimal("13000"),
        market_value_usd=None,
        realized_notional=Decimal("0"),
        realized_pnl_usd=Decimal("0"),
        unrealized_pnl_usd=None,
        updated_at=datetime.now(tz=timezone.utc),
        source_event="executionReport",
    )
    service = SpotAccountStateService()

    refreshed = await service.refresh_position_mark(
        session,  # type: ignore[arg-type]
        position,
    )

    assert refreshed.last_mark_price == Decimal("66000")
    assert refreshed.market_value_usd == Decimal("13200.0")
    assert refreshed.unrealized_pnl_usd == Decimal("200.0")
