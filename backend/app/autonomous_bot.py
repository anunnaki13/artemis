"""
AIQ Autonomous Trading Bot - Main Orchestrator
24/7 autonomous trading with multi-strategy ensemble
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_session
from services.execution.bybit_runtime import resolve_bybit_execution_runtime
from services.execution.intent_queue import ExecutionIntentQueueService
from strategies.base import StrategySignal
from strategies.ema_momentum import EMAMomentumStrategy
from strategies.rsi_bounce import RSIBounceStrategy
from strategies.vwap_reversion import VWAPReversionStrategy
from strategies.breakout_volume import BreakoutVolumeStrategy
from services.market_data.bybit_streaming import BybitStreamService
from services.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class AutonomousTradingBot:
    """
    Main orchestrator for 24/7 autonomous trading on Bybit.
    Combines multiple strategies with ensemble voting and strict risk management.
    """
    
    def __init__(self):
        self.strategies = [
            EMAMomentumStrategy(),
            RSIBounceStrategy(),
            VWAPReversionStrategy(),
            BreakoutVolumeStrategy(),
        ]
        self.intent_queue = ExecutionIntentQueueService()
        self.risk_manager = RiskManager()
        self.stream_service: Optional[BybitStreamService] = None
        self.is_running = False
        self.session: Optional[AsyncSession] = None
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self.scan_interval = 60  # seconds
        
    async def initialize(self, session: AsyncSession):
        """Initialize the bot with database session and runtime."""
        self.session = session
        self.stream_service = BybitStreamService()
        
        # Verify Bybit runtime is configured
        runtime = await resolve_bybit_execution_runtime(session)
        if not runtime or not runtime.api_key:
            logger.error("Bybit credentials not configured. Cannot start autonomous trading.")
            raise ValueError("Bybit credentials required for autonomous trading")
        
        logger.info(f"Autonomous bot initialized with {len(self.strategies)} strategies")
        logger.info(f"Trading symbols: {self.symbols}")
        
    async def scan_market(self, symbol: str) -> list[StrategySignal]:
        """
        Scan market for a single symbol across all strategies.
        Returns list of signals from all strategies.
        """
        signals = []
        
        for strategy in self.strategies:
            try:
                signal = await strategy.generate_signal(symbol, self.session)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error in strategy {strategy.name} for {symbol}: {e}")
                
        return signals
    
    def ensemble_vote(self, signals: list[StrategySignal]) -> Optional[StrategySignal]:
        """
        Ensemble voting system to filter high-probability signals.
        Requires at least 2 strategies agreeing on direction.
        """
        if not signals:
            return None
            
        long_votes = sum(1 for s in signals if s.direction == "LONG")
        short_votes = sum(1 for s in signals if s.direction == "SHORT")
        
        # Require consensus (at least 2 strategies agree)
        threshold = 2
        
        if long_votes >= threshold:
            # Average the confidence scores
            avg_confidence = sum(s.confidence for s in signals if s.direction == "LONG") / long_votes
            best_signal = max([s for s in signals if s.direction == "LONG"], key=lambda x: x.confidence)
            best_signal.confidence = avg_confidence
            return best_signal
            
        elif short_votes >= threshold:
            avg_confidence = sum(s.confidence for s in signals if s.direction == "SHORT") / short_votes
            best_signal = max([s for s in signals if s.direction == "SHORT"], key=lambda x: x.confidence)
            best_signal.confidence = avg_confidence
            return best_signal
            
        return None
    
    async def execute_signal(self, signal: StrategySignal):
        """Execute a trading signal with full risk management."""
        
        # Pre-trade risk checks
        risk_check = await self.risk_manager.pre_trade_check(
            symbol=signal.symbol,
            direction=signal.direction,
            proposed_notional=signal.position_size_usd,
            session=self.session
        )
        
        if not risk_check.approved:
            logger.warning(f"Trade rejected by risk manager: {risk_check.reason}")
            return
            
        # Create execution intent
        intent_id = await self.intent_queue.create_intent(
            symbol=signal.symbol,
            side="BUY" if signal.direction == "LONG" else "SELL",
            target_notional=signal.position_size_usd,
            source_strategy=f"autonomous_{signal.strategy_name}",
            reasoning=signal.reasoning,
            metadata={
                "confidence": signal.confidence,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
            },
            session=self.session
        )
        
        logger.info(f"Created intent {intent_id} for {signal.symbol} {signal.direction}")
        
        # Approve and dispatch
        await self.intent_queue.approve_intent(intent_id, session=self.session)
        await self.intent_queue.dispatch_intent(intent_id, session=self.session)
        
    async def trading_loop(self):
        """Main autonomous trading loop running 24/7."""
        logger.info("Starting autonomous trading loop...")
        
        while self.is_running:
            try:
                for symbol in self.symbols:
                    if not self.is_running:
                        break
                        
                    # Scan market for signals
                    signals = await self.scan_market(symbol)
                    
                    if signals:
                        # Apply ensemble voting
                        consensus_signal = self.ensemble_vote(signals)
                        
                        if consensus_signal:
                            logger.info(
                                f"Consensus signal for {symbol}: "
                                f"{consensus_signal.direction} with {consensus_signal.confidence:.2f} confidence"
                            )
                            
                            # Execute if confidence is high enough
                            if consensus_signal.confidence >= 0.6:
                                await self.execute_signal(consensus_signal)
                                
                # Wait for next scan
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                # Don't stop on errors, just log and continue
                await asyncio.sleep(10)
                
    async def start(self):
        """Start the autonomous bot."""
        if self.is_running:
            logger.warning("Bot already running")
            return
            
        self.session = await anext(get_session())
        await self.initialize(self.session)
        
        self.is_running = True
        logger.info("Autonomous bot STARTED")
        
        # Start the trading loop
        await self.trading_loop()
        
    async def stop(self):
        """Stop the autonomous bot gracefully."""
        logger.info("Stopping autonomous bot...")
        self.is_running = False
        
        if self.session:
            await self.session.close()
            
        logger.info("Autonomous bot STOPPED")
        
    def get_status(self) -> dict:
        """Get current bot status."""
        return {
            "is_running": self.is_running,
            "strategies_count": len(self.strategies),
            "symbols": self.symbols,
            "scan_interval_seconds": self.scan_interval,
            "strategies": [s.name for s in self.strategies],
        }


# Global instance
autonomous_bot = AutonomousTradingBot()
