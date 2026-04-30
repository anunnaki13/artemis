from decimal import Decimal

from services.market_data.binance import extract_symbol_filters, parse_kline


def test_extract_symbol_filters() -> None:
    payload = {
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01000000"},
            {"filterType": "LOT_SIZE", "stepSize": "0.00010000"},
            {"filterType": "MIN_NOTIONAL", "minNotional": "5.00000000"},
        ]
    }
    assert extract_symbol_filters(payload) == {
        "tick_size": Decimal("0.01000000"),
        "step_size": Decimal("0.00010000"),
        "min_notional": Decimal("5.00000000"),
    }


def test_parse_kline() -> None:
    parsed = parse_kline(
        "btcusdt",
        "1m",
        [
            1714492800000,
            "60000.00",
            "60100.00",
            "59900.00",
            "60050.00",
            "12.50",
            1714492859999,
            "750000.00",
            1234,
        ],
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["timeframe"] == "1m"
    assert parsed["close"] == Decimal("60050.00")
    assert parsed["trade_count"] == 1234
