from decimal import Decimal

from app.schemas.risk import CapitalProfileResponse
from services.risk.capital_profile import CapitalProfileManager
from services.risk.signal_gate import SignalRiskGate, SignalRiskInput
from strategies.base import Signal


def build_capital_profile(current_equity: Decimal) -> CapitalProfileResponse:
    manager = CapitalProfileManager("/home/damnation/trade/config/capital_profiles.yaml")
    return manager.evaluate(current_equity)


def test_signal_risk_gate_allows_valid_standard_signal() -> None:
    signal = Signal(
        symbol="BTCUSDT",
        side="long",
        conviction=0.8,
        source="orderbook_imbalance",
        regime="microstructure",
        suggested_stop=99.0,
        suggested_take_profit=103.0,
    )
    decision = SignalRiskGate().evaluate(
        SignalRiskInput(
            signal=signal,
            current_equity=Decimal("10000"),
            entry_price=Decimal("100"),
            proposed_notional=Decimal("500"),
            current_open_positions=1,
            current_total_exposure_notional=Decimal("500"),
            daily_pnl_pct=Decimal("0"),
            leverage=Decimal("1"),
            quote_volume_usd=Decimal("50000000"),
            use_futures=False,
        ),
        build_capital_profile(Decimal("10000")),
    )

    assert decision.allowed is True
    assert decision.computed_r_multiple == Decimal("3")
    assert decision.evaluated_open_positions == 1
    assert decision.evaluated_total_exposure_notional == Decimal("500")


def test_signal_risk_gate_blocks_micro_profile_for_multiple_reasons() -> None:
    signal = Signal(
        symbol="BTCUSDT",
        side="long",
        conviction=0.8,
        source="high_frequency_scalping",
        regime="microstructure",
        suggested_stop=99.5,
        suggested_take_profit=100.5,
    )
    decision = SignalRiskGate().evaluate(
        SignalRiskInput(
            signal=signal,
            current_equity=Decimal("100"),
            entry_price=Decimal("100"),
            proposed_notional=Decimal("20"),
            current_open_positions=1,
            current_total_exposure_notional=Decimal("95"),
            daily_pnl_pct=Decimal("-0.06"),
            leverage=Decimal("4"),
            quote_volume_usd=Decimal("1000000"),
            use_futures=True,
        ),
        build_capital_profile(Decimal("100")),
    )

    assert decision.allowed is False
    assert "strategy is forbidden for active capital profile" in decision.reasons
    assert "proposed leverage exceeds hard max leverage" in decision.reasons
    assert "daily pnl breaches absolute max daily loss" in decision.reasons
    assert "futures usage is blocked for active capital profile" in decision.reasons
    assert "trade target R is below capital profile minimum" in decision.reasons
    assert "proposed trade exceeds hard max total exposure" in decision.reasons
