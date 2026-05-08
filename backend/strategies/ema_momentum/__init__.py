"""
EMA Momentum Strategy - Trend following using EMA crossovers
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from strategies.base import Signal, DataRequirements, Strategy
from app.models import MarketSnapshot

logger = logging.getLogger(__name__)


class EMAMomentumStrategy(Strategy):
    """
    EMA Crossover Momentum Strategy.
    Generates signals based on fast/slow EMA crossovers with trend confirmation.
    """
    
    name = "ema_momentum"
    version = "1.0.0"
    parameter_schema = {
        "fast_period": {"type": "int", "default": 9},
        "slow_period": {"type": "int", "default": 21},
        "trend_period": {"type": "int", "default": 50},
        "min_conviction": {"type": "float", "default": 0.55},
    }
    
    def __init__(self):
        self.fast_period = 9
        self.slow_period = 21
        self.trend_period = 50
        self.min_conviction = 0.55
        
    def required_data(self) -> DataRequirements:
        return DataRequirements(
            timeframes=["1m", "5m", "15m"],
            lookback=100,
            needs_orderbook=False,
            needs_funding=False
        )
        
    def calculate_ema(self, prices: list[float], period: int) -> Optional[float]:
        """Calculate EMA for a given period."""
        if len(prices) < period:
            return None
            
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
            
        return ema
        
    async def get_candle_data(self, symbol: str, session: AsyncSession, limit: int = 100) -> list[dict]:
        """Fetch recent candle data from database."""
        result = await session.execute(
            select(MarketSnapshot)
            .where(MarketSnapshot.symbol == symbol)
            .order_by(MarketSnapshot.timestamp.desc())
            .limit(limit)
        )
        snapshots = result.scalars().all()
        
        candles = []
        for snapshot in snapshots:
            payload = snapshot.payload if isinstance(snapshot.payload, dict) else {}
            if "candles" in payload:
                candles.extend(payload["candles"])
                
        candles.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return candles[:limit]
        
    async def generate_signal(self, market_data: Any, params: dict[str, Any]) -> Signal | None:
        return None
        
    async def generate_signal_for_symbol(self, symbol: str, session: AsyncSession) -> Optional[Signal]:
        """Generate signal for a specific symbol."""
        try:
            candles = await self.get_candle_data(symbol, session, limit=100)
            
            if len(candles) < self.trend_period:
                return None
                
            closes = [float(candle.get("close", 0)) for candle in candles if candle.get("close")]
            
            if len(closes) < self.trend_period:
                return None
                
            fast_ema = self.calculate_ema(closes, self.fast_period)
            slow_ema = self.calculate_ema(closes, self.slow_period)
            trend_ema = self.calculate_ema(closes, self.trend_period)
            
            if not all([fast_ema, slow_ema, trend_ema]):
                return None
                
            current_price = closes[0]
            side = None
            conviction = 0.0
            
            if fast_ema > slow_ema and current_price > trend_ema:
                side = "long"
                ema_sep = (fast_ema - slow_ema) / slow_ema
                conviction = min(0.9, 0.5 + abs(ema_sep) * 10)
            elif fast_ema < slow_ema and current_price < trend_ema:
                side = "short"
                ema_sep = (slow_ema - fast_ema) / slow_ema
                conviction = min(0.9, 0.5 + abs(ema_sep) * 10)
                
            if conviction < self.min_conviction:
                return None
                
            atr = self.calculate_atr(closes, period=14) or (current_price * 0.02)
            
            if side == "long":
                stop_loss = current_price - (atr * 1.5)
                take_profit = current_price + (atr * 3)
            else:
                stop_loss = current_price + (atr * 1.5)
                take_profit = current_price - (atr * 3)
                
            return Signal(
                symbol=symbol,
                side=side,
                conviction=conviction,
                source=self.name,
                regime="trending",
                suggested_stop=stop_loss,
                suggested_take_profit=take_profit,
                metadata={
                    "fast_ema": fast_ema,
                    "slow_ema": slow_ema,
                    "trend_ema": trend_ema,
                    "entry_price": current_price,
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating EMA signal for {symbol}: {e}")
            return None
            
    def calculate_atr(self, prices: list[float], period: int = 14) -> Optional[float]:
        """Calculate Average True Range (simplified)."""
        if len(prices) < period + 1:
            return None
            
        true_ranges = []
        for i in range(1, len(prices)):
            high_low = abs(prices[i-1] - prices[i])
            true_ranges.append(high_low)
            
        if not true_ranges:
            return None
            
        return sum(true_ranges[-period:]) / period
