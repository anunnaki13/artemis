from services.edge.universe_manager import SymbolUniverseManager


def test_universe_manager_filters_and_ranks_symbols() -> None:
    manager = SymbolUniverseManager("../config/edge/universe.yaml", "../config/edge/blacklist.yaml")
    selection = manager.select(
        [
            {"symbol": "AAAUSDT", "quoteVolume": "30000000", "priceChangePercent": "1.2"},
            {"symbol": "BBBUSDT", "quoteVolume": "150000000", "priceChangePercent": "-2.5"},
            {"symbol": "CCCUSDT", "quoteVolume": "1000000", "priceChangePercent": "0.1"},
            {"symbol": "USDCUSDT", "quoteVolume": "90000000", "priceChangePercent": "0.0"},
            {"symbol": "DDDBTC", "quoteVolume": "90000000", "priceChangePercent": "0.0"},
        ]
    )

    assert [candidate.symbol for candidate in selection.candidates] == ["BBBUSDT", "AAAUSDT"]
    assert selection.rejected_count == 3


def test_universe_manager_excludes_stablecoin_bases() -> None:
    manager = SymbolUniverseManager("../config/edge/universe.yaml", "../config/edge/blacklist.yaml")
    selection = manager.select(
        [{"symbol": "DAIUSDT", "quoteVolume": "30000000", "priceChangePercent": "0.0"}]
    )
    assert selection.candidates == []
    assert selection.rejected_count == 1
