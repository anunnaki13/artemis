from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field


class Signal(BaseModel):
    symbol: str
    side: Literal["long", "short"]
    conviction: float = Field(ge=0.0, le=1.0)
    source: str
    regime: str
    suggested_stop: float | None = None
    suggested_take_profit: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataRequirements(BaseModel):
    timeframes: list[str]
    lookback: int
    needs_orderbook: bool = False
    needs_funding: bool = False


class Strategy(ABC):
    name: str
    version: str
    parameter_schema: dict[str, Any]

    @abstractmethod
    async def generate_signal(self, market_data: Any, params: dict[str, Any]) -> Signal | None:
        raise NotImplementedError

    @abstractmethod
    def required_data(self) -> DataRequirements:
        raise NotImplementedError

