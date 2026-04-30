from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from app.schemas.risk import CapitalProfileRead, CapitalProfileResponse, FeeStrategyRead


class CapitalProfileManager:
    def __init__(self, profile_path: str) -> None:
        self.profile_path = Path(profile_path)

    def evaluate(self, current_equity: Decimal) -> CapitalProfileResponse:
        config = self._load_config()
        profiles = [
            self._profile_from_config(name, payload)
            for name, payload in config.get("profiles", {}).items()
            if isinstance(payload, dict)
        ]
        active_profile = self._select_profile(current_equity, profiles)
        return CapitalProfileResponse(
            current_equity=current_equity,
            active_profile=active_profile,
            fee_strategy=FeeStrategyRead.model_validate(config["fee_strategy"]),
            enforcement_notes=self._enforcement_notes(active_profile),
        )

    def _load_config(self) -> dict[str, Any]:
        with self.profile_path.open(encoding="utf-8") as file:
            payload = yaml.safe_load(file)
        if not isinstance(payload, dict):
            raise ValueError("capital profile config must be a mapping")
        return payload

    def _profile_from_config(self, name: str, payload: dict[str, Any]) -> CapitalProfileRead:
        return CapitalProfileRead.model_validate({"name": name.upper(), **payload})

    def _select_profile(
        self,
        current_equity: Decimal,
        profiles: list[CapitalProfileRead],
    ) -> CapitalProfileRead:
        for profile in sorted(profiles, key=lambda item: item.equity_min):
            below_max = profile.equity_max is None or current_equity < profile.equity_max
            if current_equity >= profile.equity_min and below_max:
                return profile
        return min(profiles, key=lambda item: item.equity_min)

    def _enforcement_notes(self, profile: CapitalProfileRead) -> list[str]:
        notes = [
            f"max concurrent positions: {profile.max_concurrent_positions}",
            f"risk per trade: {profile.risk_per_trade_pct}%",
            f"default fee tier preference: {profile.preferred_fee_tier}",
        ]
        if profile.name == "MICRO":
            notes.extend(
                [
                    "force maker-first execution",
                    "block forbidden micro-profile strategies",
                    "keep idle capital in stablecoin",
                ]
            )
        return notes
