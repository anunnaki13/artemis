from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class UniverseCandidate:
    symbol: str
    base_asset: str
    quote_asset: str
    quote_volume: Decimal
    price_change_pct: Decimal


@dataclass(frozen=True)
class UniverseSelection:
    candidates: list[UniverseCandidate]
    rejected_count: int
    min_quote_volume_usd: Decimal
    max_quote_volume_usd: Decimal


class SymbolUniverseManager:
    def __init__(self, config_path: str, blacklist_path: str) -> None:
        self.config_path = Path(config_path)
        self.blacklist_path = Path(blacklist_path)

    def select(self, tickers: list[dict[str, Any]]) -> UniverseSelection:
        config = self._load_yaml(self.config_path)
        blacklist = self._load_yaml(self.blacklist_path)
        blacklisted_symbols = set(blacklist.get("symbols", []))
        quote_assets = set(config.get("quote_assets", ["USDT"]))
        stablecoin_bases = set(config.get("exclude_stablecoin_bases", []))
        min_volume = Decimal(str(config["min_quote_volume_usd"]))
        max_volume = Decimal(str(config["max_quote_volume_usd"]))
        max_symbols = int(config["max_symbols"])

        candidates: list[UniverseCandidate] = []
        rejected_count = 0
        for ticker in tickers:
            symbol = str(ticker.get("symbol", ""))
            quote_asset = self._quote_asset(symbol, quote_assets)
            if quote_asset is None or symbol in blacklisted_symbols:
                rejected_count += 1
                continue
            base_asset = symbol.removesuffix(quote_asset)
            if base_asset in stablecoin_bases:
                rejected_count += 1
                continue
            quote_volume = Decimal(str(ticker.get("quoteVolume", "0")))
            if quote_volume < min_volume or quote_volume > max_volume:
                rejected_count += 1
                continue
            candidates.append(
                UniverseCandidate(
                    symbol=symbol,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    quote_volume=quote_volume,
                    price_change_pct=Decimal(str(ticker.get("priceChangePercent", "0"))),
                )
            )

        ranked = sorted(candidates, key=lambda item: item.quote_volume, reverse=True)[:max_symbols]
        return UniverseSelection(
            candidates=ranked,
            rejected_count=rejected_count,
            min_quote_volume_usd=min_volume,
            max_quote_volume_usd=max_volume,
        )

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as file:
            payload = yaml.safe_load(file)
        if not isinstance(payload, dict):
            raise ValueError(f"{path} must contain a mapping")
        return payload

    def _quote_asset(self, symbol: str, quote_assets: set[str]) -> str | None:
        for quote_asset in quote_assets:
            if symbol.endswith(quote_asset):
                return quote_asset
        return None
