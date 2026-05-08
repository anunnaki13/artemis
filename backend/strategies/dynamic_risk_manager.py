"""
Dynamic Risk Manager
Features:
- Kelly Criterion Position Sizing
- Volatility-based sizing (ATR)
- Drawdown protection
- Daily loss limits
- Win/Loss streak adjustments
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta

class DynamicRiskManager:
    """
    Manages position sizing and risk dynamically based on:
    1. Account equity
    2. Recent performance (win rate)
    3. Market volatility (ATR)
    4. Drawdown status
    """
    
    def __init__(self, 
                 initial_capital: float = 1000.0,
                 max_daily_loss_pct: float = 0.05,  # 5% max daily loss
                 max_position_pct: float = 0.20,    # Max 20% per trade
                 min_position_pct: float = 0.02,    # Min 2% per trade
                 kelly_fraction: float = 0.25):     # Use 25% of Kelly (conservative)
        
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_position_pct = max_position_pct
        self.min_position_pct = min_position_pct
        self.kelly_fraction = kelly_fraction
        
        # Tracking
        self.daily_pnl = 0.0
        self.daily_start_capital = initial_capital
        self.trade_history = []  # List of {'result': 'win'/'loss', 'pnl': float, 'timestamp': datetime}
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.max_drawdown_pct = 0.0
        self.current_drawdown_pct = 0.0
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.avg_win = 0.0
        self.avg_loss = 0.0
    
    def reset_daily(self):
        """Reset daily PnL tracking (call at start of new day)"""
        self.daily_pnl = 0.0
        self.daily_start_capital = self.current_capital
    
    def record_trade(self, pnl: float):
        """Record a completed trade for performance tracking"""
        is_win = pnl > 0
        self.trade_history.append({
            'result': 'win' if is_win else 'loss',
            'pnl': pnl,
            'timestamp': datetime.now()
        })
        
        self.total_trades += 1
        if is_win:
            self.winning_trades += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            # Update average win
            self.avg_win = ((self.avg_win * (self.winning_trades - 1)) + pnl) / self.winning_trades
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            # Count losses
            total_losses = self.total_trades - self.winning_trades
            self.avg_loss = ((self.avg_loss * (total_losses - 1)) + abs(pnl)) / total_losses
        
        # Update capital
        self.current_capital += pnl
        self.daily_pnl += pnl
        
        # Update drawdown
        peak = max([t['pnl'] for t in self.trade_history] + [0])
        if self.current_capital < self.initial_capital:
            self.current_drawdown_pct = (self.initial_capital - self.current_capital) / self.initial_capital
            self.max_drawdown_pct = max(self.max_drawdown_pct, self.current_drawdown_pct)
    
    def can_trade(self) -> tuple[bool, str]:
        """Check if trading is allowed based on risk limits"""
        # Check daily loss limit
        daily_loss_pct = abs(min(0, self.daily_pnl)) / self.daily_start_capital
        if daily_loss_pct >= self.max_daily_loss_pct:
            return False, f"Daily loss limit reached ({daily_loss_pct*100:.2f}%)"
        
        # Check max drawdown
        if self.max_drawdown_pct >= 0.20:  # 20% max drawdown
            return False, f"Max drawdown reached ({self.max_drawdown_pct*100:.2f}%)"
        
        # Check consecutive losses
        if self.consecutive_losses >= 5:
            return False, "5 consecutive losses - cooling off period"
        
        return True, "OK"
    
    def calculate_position_size(self, 
                                current_price: float, 
                                atr: Optional[float] = None,
                                stop_loss_pct: Optional[float] = None) -> Dict:
        """
        Calculate optimal position size using Kelly Criterion + Volatility adjustment
        
        Returns: {
            'position_size_usd': float,
            'position_pct': float,
            'quantity': float,
            'stop_loss_price': float,
            'take_profit_price': float,
            'risk_reasoning': str
        }
        """
        can_trade, reason = self.can_trade()
        if not can_trade:
            return {
                'position_size_usd': 0,
                'position_pct': 0,
                'quantity': 0,
                'stop_loss_price': 0,
                'take_profit_price': 0,
                'risk_reasoning': reason
            }
        
        # 1. Calculate Win Rate
        if self.total_trades < 5:
            # Not enough data, use conservative estimate
            win_rate = 0.5
        else:
            win_rate = self.winning_trades / self.total_trades
        
        # 2. Calculate Profit Factor (Avg Win / Avg Loss)
        if self.avg_loss == 0:
            profit_factor = 2.0  # Assume favorable if no losses yet
        else:
            profit_factor = self.avg_win / self.avg_loss if self.avg_win > 0 else 0.5
        
        # 3. Kelly Criterion Formula: K% = W - [(1-W)/R]
        # W = Win probability, R = Win/Loss ratio
        if profit_factor > 0:
            kelly_pct = win_rate - ((1 - win_rate) / profit_factor)
        else:
            kelly_pct = 0
        
        # Apply conservative fraction (e.g., 25% of Kelly)
        kelly_pct = kelly_pct * self.kelly_fraction
        
        # Ensure positive
        kelly_pct = max(0, kelly_pct)
        
        # 4. Adjust for Volatility (if ATR provided)
        volatility_adjustment = 1.0
        if atr and current_price:
            # Normalize ATR (assume typical crypto ATR is 2-5% of price)
            atr_pct = atr / current_price
            if atr_pct > 0.05:  # High volatility
                volatility_adjustment = 0.7
            elif atr_pct < 0.02:  # Low volatility
                volatility_adjustment = 1.2
            
        # 5. Adjust for Streaks
        streak_adjustment = 1.0
        if self.consecutive_losses >= 3:
            streak_adjustment = 0.5  # Reduce size after 3 losses
        elif self.consecutive_wins >= 3:
            streak_adjustment = 1.1  # Slightly increase after 3 wins
        
        # Final position percentage
        position_pct = kelly_pct * volatility_adjustment * streak_adjustment
        
        # Apply limits
        position_pct = max(self.min_position_pct, min(position_pct, self.max_position_pct))
        
        # If no historical data, use base position
        if self.total_trades < 5:
            position_pct = self.min_position_pct
        
        # Calculate USD size
        position_size_usd = self.current_capital * position_pct
        
        # Calculate quantity
        quantity = position_size_usd / current_price if current_price > 0 else 0
        
        # Calculate Stop Loss and Take Profit
        stop_loss_price = 0
        take_profit_price = 0
        
        if stop_loss_pct:
            stop_loss_price = current_price * (1 - stop_loss_pct)
            # Risk:Reward ratio of 1:2
            take_profit_price = current_price * (1 + (stop_loss_pct * 2))
        elif atr:
            # Use ATR-based stops
            stop_loss_price = current_price - (2 * atr)
            take_profit_price = current_price + (4 * atr)
        
        reasoning = (
            f"WinRate:{win_rate*100:.1f}% | "
            f"Kelly:{kelly_pct*100:.2f}% | "
            f"VolAdj:{volatility_adjustment} | "
            f"StreakAdj:{streak_adjustment} | "
            f"ConsecLoss:{self.consecutive_losses}"
        )
        
        return {
            'position_size_usd': round(position_size_usd, 2),
            'position_pct': round(position_pct * 100, 2),
            'quantity': round(quantity, 8),
            'stop_loss_price': round(stop_loss_price, 2) if stop_loss_price else None,
            'take_profit_price': round(take_profit_price, 2) if take_profit_price else None,
            'stop_loss_pct': stop_loss_pct if stop_loss_pct else None,
            'risk_reasoning': reasoning
        }
    
    def get_performance_summary(self) -> Dict:
        """Get current performance metrics"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        total_pnl = self.current_capital - self.initial_capital
        total_pnl_pct = (total_pnl / self.initial_capital * 100)
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.total_trades - self.winning_trades,
            'win_rate_pct': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl_pct, 2),
            'current_capital': round(self.current_capital, 2),
            'max_drawdown_pct': round(self.max_drawdown_pct * 100, 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'avg_win': round(self.avg_win, 2),
            'avg_loss': round(self.avg_loss, 2),
            'profit_factor': round(self.avg_win / self.avg_loss, 2) if self.avg_loss > 0 else 0
        }


# Example Usage
if __name__ == "__main__":
    risk_mgr = DynamicRiskManager(initial_capital=1000.0)
    
    # Simulate some trades
    for i in range(10):
        pnl = np.random.choice([-15, -10, -5, 5, 10, 20, 30])
        risk_mgr.record_trade(pnl)
        
        # Calculate position for next trade
        pos = risk_mgr.calculate_position_size(
            current_price=50000, 
            atr=800,
            stop_loss_pct=0.02
        )
        
        print(f"Trade {i+1}: PnL={pnl}, Next Position: ${pos['position_size_usd']} ({pos['position_pct']}%)")
        print(f"  Reasoning: {pos['risk_reasoning']}")
    
    print("\n=== Performance Summary ===")
    summary = risk_mgr.get_performance_summary()
    for k, v in summary.items():
        print(f"{k}: {v}")
