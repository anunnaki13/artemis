from decimal import Decimal

from services.risk.capital_profile import CapitalProfileManager


def test_capital_profile_manager_returns_micro_for_100_usd() -> None:
    manager = CapitalProfileManager("../config/capital_profiles.yaml")
    response = manager.evaluate(Decimal("100"))
    assert response.active_profile.name == "MICRO"
    assert response.active_profile.max_concurrent_positions == 1
    assert response.active_profile.risk_per_trade_pct == Decimal("2.0")
    assert response.active_profile.use_futures is False
    assert "force maker-first execution" in response.enforcement_notes


def test_capital_profile_manager_returns_scaled_for_large_equity() -> None:
    manager = CapitalProfileManager("../config/capital_profiles.yaml")
    response = manager.evaluate(Decimal("75000"))
    assert response.active_profile.name == "SCALED"
    assert response.active_profile.max_concurrent_positions == 5
