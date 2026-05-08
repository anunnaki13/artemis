"""
Risk Manager - Pre-trade and portfolio risk controls
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import SpotSymbolPosition, SpotAccountBalance, ExecutionIntent

logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    """Result of a pre-trade risk check."""
    approved: bool
    reason: Optional[str] = None
    max_position_usd: Optional[Decimal] = None
    current_exposure_usd: Optional[Decimal] = None
    available_capital_usd: Optional[Decimal] = None


class RiskManager:
    """
    Centralized risk management for autonomous trading.
    Implements multiple layers of risk controls.
    """
    
    # Risk limits (configurable)
    MAX_POSITION_SIZE_USD = Decimal("1000")  # Max per position
    MAX_TOTAL_EXPOSURE_USD = Decimal("3000")  # Max total exposure
    MAX_DAILY_LOSS_USD = Decimal("200")  # Max daily loss before halt
    POSITION_SIZE_PCT_OF_EQUITY = Decimal("0.10")  # Max 10% of equity per position
    CORRELATION_LIMIT = 3  # Max positions in correlated assets
    
    def __init__(self):
        self.daily_loss_start: Optional[Decimal] = None
        self.daily_pnl: Decimal = Decimal("0")
        
    async def get_account_equity(self, session: AsyncSession) -> Decimal:
        """Get total account equity in USD."""
        result = await session.execute(
            select(func.sum(SpotAccountBalance.total_value_usd))
        )
        equity = result.scalar() or Decimal("0")
        return equity
        
    async def get_current_exposure(self, session: AsyncSession) -> Decimal:
        """Get current total exposure from open positions."""
        result = await session.execute(
            select(func.sum(SpotSymbolPosition.quote_exposure_usd))
        )
        exposure = result.scalar() or Decimal("0")
        return exposure
        
    async def get_position_size(self, session: AsyncSession, symbol: str) -> Decimal:
        """Get current position size for a symbol."""
        result = await session.execute(
            select(SpotSymbolPosition.quote_exposure_usd)
            .where(SpotSymbolPosition.symbol == symbol)
        )
        position = result.scalar() or Decimal("0")
        return abs(position)
        
    async def get_daily_pnl(self, session: AsyncSession) -> Decimal:
        """Calculate daily PnL from realized fills today."""
        from datetime import datetime, timezone
        
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        # Get all fills today
        from app.models import SpotExecutionFill
        result = await session.execute(
            select(
                func.sum(SpotExecutionFill.realized_pnl_usd)
            ).where(
                SpotExecutionFill.filled_at >= today_start
            )
        )
        daily_pnl = result.scalar() or Decimal("0")
        return daily_pnl
        
    async def pre_trade_check(
        self,
        symbol: str,
        direction: str,
        proposed_notional: Decimal,
        session: AsyncSession
    ) -> RiskCheckResult:
        """
        Perform comprehensive pre-trade risk check.
        Returns RiskCheckResult with approval status and reasoning.
        """
        
        # Get current account state
        equity = await self.get_account_equity(session)
        current_exposure = await self.get_current_exposure(session)
        current_position = await self.get_position_size(session, symbol)
        daily_pnl = await self.get_daily_pnl(session)
        
        # Calculate dynamic position limit based on equity
        dynamic_max_position = equity * self.POSITION_SIZE_PCT_OF_EQUITY
        effective_max_position = min(self.MAX_POSITION_SIZE_USD, dynamic_max_position)
        
        logger.info(
            f"Pre-trade check for {symbol} {direction}: "
            f"proposed={proposed_notional}, equity={equity}, exposure={current_exposure}"
        )
        
        # Check 1: Daily loss limit
        if daily_pnl < -self.MAX_DAILY_LOSS_USD:
            return RiskCheckResult(
                approved=False,
                reason=f"Daily loss limit exceeded: {daily_pnl} < -{self.MAX_DAILY_LOSS_USD}",
                current_exposure_usd=current_exposure,
                available_capital_usd=equity
            )
            
        # Check 2: Position size limit
        if proposed_notional > effective_max_position:
            return RiskCheckResult(
                approved=False,
                reason=f"Position size {proposed_notional} exceeds limit {effective_max_position}",
                max_position_usd=effective_max_position,
                current_exposure_usd=current_exposure,
                available_capital_usd=equity
            )
            
        # Check 3: Total exposure limit
        new_exposure = current_exposure + proposed_notional
        if new_exposure > self.MAX_TOTAL_EXPOSURE_USD:
            return RiskCheckResult(
                approved=False,
                reason=f"Total exposure {new_exposure} would exceed limit {self.MAX_TOTAL_EXPOSURE_USD}",
                max_position_usd=effective_max_position,
                current_exposure_usd=current_exposure,
                available_capital_usd=equity
            )
            
        # Check 4: Existing position (avoid doubling down without signal)
        if current_position > Decimal("0"):
            # Allow adding to position but warn
            if current_position * Decimal("2") < proposed_notional:
                logger.warning(f"Adding to existing position in {symbol}")
                
        # Check 5: Minimum capital requirement
        if equity < Decimal("100"):
            return RiskCheckResult(
                approved=False,
                reason=f"Insufficient equity: {equity} < 100 USDT minimum",
                current_exposure_usd=current_exposure,
                available_capital_usd=equity
            )
            
        # All checks passed
        return RiskCheckResult(
            approved=True,
            max_position_usd=effective_max_position,
            current_exposure_usd=current_exposure,
            available_capital_usd=equity
        )
        
    def calculate_position_size(
        self,
        equity: Decimal,
        volatility: Decimal,
        confidence: float
    ) -> Decimal:
        """
        Calculate optimal position size using Kelly Criterion approximation.
        Adjusts for volatility and signal confidence.
        """
        # Base position: fraction of equity
        base_size = equity * self.POSITION_SIZE_PCT_OF_EQUITY
        
        # Adjust for confidence (higher confidence = larger position)
        confidence_multiplier = Decimal(str(confidence))
        
        # Adjust for volatility (higher volatility = smaller position)
        volatility_adjustment = Decimal("1") / (Decimal("1") + volatility)
        
        # Final position size
        position_size = base_size * confidence_multiplier * volatility_adjustment
        
        # Apply limits
        position_size = min(position_size, self.MAX_POSITION_SIZE_USD)
        position_size = max(position_size, Decimal("10"))  # Minimum $10
        
        return position_size
        
    async def check_circuit_breaker(self, session: AsyncSession) -> tuple[bool, str]:
        """
        Check if circuit breaker should be triggered.
        Returns (should_halt, reason).
        """
        daily_pnl = await self.get_daily_pnl(session)
        
        # Hard stop: large daily loss
        if daily_pnl < -self.MAX_DAILY_LOSS_USD:
            return True, f"Daily loss limit hit: {daily_pnl}"
            
        # Soft warning: consecutive losses (would need more tracking)
        # For now, just check daily PnL
        
        return False, ""
        
    def get_risk_metrics(self) -> dict:
        """Get current risk metrics summary."""
        return {
            "max_position_usd": str(self.MAX_POSITION_SIZE_USD),
            "max_total_exposure_usd": str(self.MAX_TOTAL_EXPOSURE_USD),
            "max_daily_loss_usd": str(self.MAX_DAILY_LOSS_USD),
            "position_size_pct": str(self.POSITION_SIZE_PCT_OF_EQUITY),
        }


# Global instance
risk_manager = RiskManager()
