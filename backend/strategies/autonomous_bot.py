"""
Autonomous Trading Bot - Main Loop
Features:
- 24/7 trading with Bybit
- Multi-strategy ensemble
- Dynamic risk management
- Auto-recovery and monitoring
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import pandas as pd

from strategies.advanced_engine import StrategyEnsemble, MarketRegime
from strategies.dynamic_risk_manager import DynamicRiskManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutonomousTradingBot:
    """
    Main autonomous trading bot that runs 24/7
    """
    
    def __init__(self, 
                 initial_capital: float = 1000.0,
                 symbol: str = "BTCUSDT",
                 timeframe: str = "1h",
                 check_interval: int = 60):  # Check every 60 seconds
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.check_interval = check_interval
        
        # Initialize components
        self.strategy_engine = StrategyEnsemble()
        self.risk_manager = DynamicRiskManager(initial_capital=initial_capital)
        
        # State
        self.is_running = False
        self.current_position: Optional[Dict] = None
        self.last_check: Optional[datetime] = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        # Market data cache
        self.market_data: Optional[pd.DataFrame] = None
        
        logger.info(f"AutonomousTradingBot initialized for {symbol}")
    
    async def fetch_market_data(self) -> Optional[pd.DataFrame]:
        """
        Fetch market data from Bybit (or mock data for testing)
        In production, this would use actual Bybit API
        """
        try:
            # TODO: Implement actual Bybit API call
            # For now, generate mock data for testing
            logger.info(f"Fetching market data for {self.symbol}...")
            
            # Mock data generation
            now = datetime.now()
            dates = pd.date_range(end=now, periods=100, freq=self.timeframe)
            
            # Simulate realistic price movement
            base_price = 50000
            np = __import__('numpy')
            returns = np.random.normal(0.001, 0.02, 100)
            prices = base_price * np.cumprod(1 + returns)
            
            df = pd.DataFrame({
                'timestamp': dates,
                'open': prices,
                'high': prices * (1 + np.random.uniform(0, 0.01, 100)),
                'low': prices * (1 - np.random.uniform(0, 0.01, 100)),
                'close': prices
            })
            
            self.market_data = df
            self.consecutive_errors = 0
            return df
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            self.consecutive_errors += 1
            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.critical("Max consecutive errors reached. Stopping bot.")
                self.is_running = False
            return None
    
    async def analyze_market(self) -> Dict:
        """
        Analyze market using strategy ensemble
        """
        if self.market_data is None or len(self.market_data) < 50:
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reasoning': 'Insufficient data',
                'regime': 'UNKNOWN'
            }
        
        analysis = self.strategy_engine.analyze(self.market_data)
        logger.info(f"Market Analysis: {analysis['signal']} (Confidence: {analysis['confidence']})")
        logger.info(f"Reasoning: {analysis['reasoning']}")
        
        return analysis
    
    async def execute_trade(self, signal: str, confidence: float):
        """
        Execute trade based on signal
        """
        if signal == 'HOLD':
            logger.info("No action - HOLD signal")
            return
        
        # Check if we can trade
        can_trade, reason = self.risk_manager.can_trade()
        if not can_trade:
            logger.warning(f"Cannot trade: {reason}")
            return
        
        # Get current price
        current_price = self.market_data['close'].iloc[-1]
        
        # Calculate ATR for volatility-adjusted sizing
        high = self.market_data['high']
        low = self.market_data['low']
        close = self.market_data['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean().iloc[-1]
        
        # Calculate position size
        position_info = self.risk_manager.calculate_position_size(
            current_price=current_price,
            atr=atr,
            stop_loss_pct=0.02  # 2% stop loss
        )
        
        if position_info['position_size_usd'] <= 0:
            logger.warning("Position size is zero - skipping trade")
            return
        
        logger.info(f"Executing {signal} order:")
        logger.info(f"  Size: ${position_info['position_size_usd']} ({position_info['position_pct']}%)")
        logger.info(f"  Quantity: {position_info['quantity']}")
        logger.info(f"  Stop Loss: ${position_info['stop_loss_price']}")
        logger.info(f"  Take Profit: ${position_info['take_profit_price']}")
        logger.info(f"  Reasoning: {position_info['risk_reasoning']}")
        
        # TODO: Implement actual Bybit order execution
        # For now, simulate the trade
        logger.info(f"[SIMULATED] {signal} order executed for {self.symbol}")
        
        # Update current position
        self.current_position = {
            'symbol': self.symbol,
            'side': signal,
            'entry_price': current_price,
            'size_usd': position_info['position_size_usd'],
            'quantity': position_info['quantity'],
            'stop_loss': position_info['stop_loss_price'],
            'take_profit': position_info['take_profit_price'],
            'opened_at': datetime.now()
        }
    
    async def manage_existing_position(self):
        """
        Manage existing position (check stop loss / take profit)
        """
        if not self.current_position:
            return
        
        current_price = self.market_data['close'].iloc[-1]
        position = self.current_position
        
        # Check stop loss
        if position['side'] == 'BUY':
            if current_price <= position['stop_loss']:
                logger.warning(f"Stop Loss hit! Closing position at ${current_price}")
                # TODO: Execute close order
                pnl = (current_price - position['entry_price']) / position['entry_price'] * position['size_usd']
                self.risk_manager.record_trade(pnl)
                self.current_position = None
                
            elif current_price >= position['take_profit']:
                logger.info(f"Take Profit hit! Closing position at ${current_price}")
                # TODO: Execute close order
                pnl = (current_price - position['entry_price']) / position['entry_price'] * position['size_usd']
                self.risk_manager.record_trade(pnl)
                self.current_position = None
        
        # Update unrealized PnL
        if self.current_position:
            if position['side'] == 'BUY':
                unrealized_pnl = (current_price - position['entry_price']) / position['entry_price'] * position['size_usd']
            else:
                unrealized_pnl = (position['entry_price'] - current_price) / position['entry_price'] * position['size_usd']
            
            logger.info(f"Unrealized PnL: ${unrealized_pnl:.2f}")
    
    async def run_loop(self):
        """
        Main trading loop - runs 24/7
        """
        logger.info("="*60)
        logger.info("AUTONOMOUS TRADING BOT STARTED")
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Initial Capital: ${self.risk_manager.initial_capital}")
        logger.info("="*60)
        
        self.is_running = True
        
        while self.is_running:
            try:
                self.last_check = datetime.now()
                logger.info(f"\n--- Check #{int((self.last_check.timestamp() - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()) / self.check_interval)} ---")
                
                # 1. Fetch market data
                await self.fetch_market_data()
                
                if self.market_data is None:
                    logger.warning("No market data available. Skipping this cycle.")
                    await asyncio.sleep(self.check_interval)
                    continue
                
                # 2. Manage existing position first
                await self.manage_existing_position()
                
                # 3. Analyze market
                analysis = await self.analyze_market()
                
                # 4. Execute trade if signal is strong enough
                if analysis['confidence'] >= 0.6:
                    await self.execute_trade(analysis['signal'], analysis['confidence'])
                else:
                    logger.info(f"Signal confidence too low ({analysis['confidence']}). Standing by.")
                
                # 5. Log performance summary
                if self.risk_manager.total_trades > 0:
                    perf = self.risk_manager.get_performance_summary()
                    logger.info(f"Performance: {perf['win_rate_pct']}% Win Rate | Total PnL: ${perf['total_pnl']:.2f}")
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received. Stopping bot...")
                self.is_running = False
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                self.consecutive_errors += 1
                if self.consecutive_errors >= self.max_consecutive_errors:
                    logger.critical("Max consecutive errors reached. Stopping bot.")
                    self.is_running = False
                else:
                    # Wait before retry
                    await asyncio.sleep(self.check_interval)
        
        logger.info("Trading bot stopped.")
        logger.info(f"Final Performance: {self.risk_manager.get_performance_summary()}")
    
    def start(self):
        """Start the bot"""
        try:
            asyncio.run(self.run_loop())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
    
    def stop(self):
        """Stop the bot"""
        self.is_running = False


# Entry point
if __name__ == "__main__":
    # Create and start bot
    bot = AutonomousTradingBot(
        initial_capital=1000.0,
        symbol="BTCUSDT",
        timeframe="1h",
        check_interval=60  # Check every 60 seconds
    )
    
    print("\n" + "="*60)
    print("AIQ AUTONOMOUS TRADING BOT")
    print("="*60)
    print("Starting 24/7 trading loop...")
    print("Press Ctrl+C to stop\n")
    
    bot.start()
