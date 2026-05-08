"""
Advanced Multi-Strategy Engine for AIQ-BOT
Supports: EMA Crossover, RSI Divergence, MACD Momentum
Features: Ensemble Voting, Regime Detection
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class MarketRegime:
    """Detects market condition: TRENDING, RANGING, or VOLATILE"""
    
    @staticmethod
    def detect(df: pd.DataFrame) -> str:
        if len(df) < 50:
            return "UNKNOWN"
        
        # Calculate ADX for trend strength
        df = MarketRegime._calculate_adx(df, period=14)
        adx = df['ADX'].iloc[-1]
        
        # Calculate Bollinger Band Width for volatility
        df = MarketRegime._calculate_bollinger(df, period=20)
        bb_width = (df['bb_upper'].iloc[-1] - df['bb_lower'].iloc[-1]) / df['bb_middle'].iloc[-1]
        
        # Logic
        if adx > 25:
            return "TRENDING"
        elif bb_width < 0.02: # Very tight bands
            return "RANGING"
        elif bb_width > 0.15: # Extremely volatile
            return "VOLATILE"
        else:
            return "NORMAL"

    @staticmethod
    def _calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        df = df.copy()
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        df['ADX'] = adx
        return df

    @staticmethod
    def _calculate_bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        df = df.copy()
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        df['bb_std'] = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)
        return df


class StrategyEnsemble:
    """
    Combines multiple strategies with weighted voting.
    Only trades when confidence is high.
    """
    
    def __init__(self):
        self.strategies = ['EMA_CROSS', 'RSI_MEAN_REV', 'MACD_MOMENTUM']
        self.weights = {
            'EMA_CROSS': 0.4,
            'RSI_MEAN_REV': 0.3,
            'MACD_MOMENTUM': 0.3
        }
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Returns: {
            'signal': 'BUY' | 'SELL' | 'HOLD',
            'confidence': 0.0 - 1.0,
            'reasoning': str,
            'regime': str
        }
        """
        if len(df) < 50:
            return {'signal': 'HOLD', 'confidence': 0.0, 'reasoning': 'Insufficient data', 'regime': 'UNKNOWN'}
        
        regime = MarketRegime.detect(df)
        
        # Don't trade in extreme volatility or unknown regimes
        if regime in ['VOLATILE', 'UNKNOWN']:
            return {'signal': 'HOLD', 'confidence': 0.0, 'reasoning': f'Market regime {regime} detected. Standing by.', 'regime': regime}
        
        votes = 0
        total_weight = 0
        reasons = []
        
        # 1. EMA Crossover Strategy (Trend Following)
        if regime == 'TRENDING':
            ema_signal, ema_weight, ema_reason = self._strategy_ema_cross(df)
            votes += ema_signal * ema_weight
            total_weight += ema_weight
            reasons.append(ema_reason)
        else:
            # Reduce weight in ranging market
            reasons.append("EMA skipped (Not trending)")
            
        # 2. RSI Mean Reversion (Good for Ranging/Normal)
        if regime in ['RANGING', 'NORMAL']:
            rsi_signal, rsi_weight, rsi_reason = self._strategy_rsi(df)
            votes += rsi_signal * rsi_weight
            total_weight += rsi_weight
            reasons.append(rsi_reason)
        
        # 3. MACD Momentum (All regimes but weaker in choppy)
        macd_signal, macd_weight, macd_reason = self._strategy_macd(df)
        # Reduce MACD weight if ranging heavily
        if regime == 'RANGING':
            macd_weight *= 0.5
        votes += macd_signal * macd_weight
        total_weight += macd_weight
        reasons.append(macd_reason)
        
        # Calculate final signal
        if total_weight == 0:
            return {'signal': 'HOLD', 'confidence': 0.0, 'reasoning': 'No strategies active', 'regime': regime}
            
        score = votes / total_weight
        
        signal = 'HOLD'
        confidence = abs(score)
        
        if score > 0.6:
            signal = 'BUY'
        elif score < -0.6:
            signal = 'SELL'
            
        reasoning = f"Regime: {regime}. " + " | ".join(reasons)
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'reasoning': reasoning,
            'regime': regime
        }

    def _strategy_ema_cross(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """Fast EMA crosses Slow EMA"""
        df = df.copy()
        df['ema_fast'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()
        
        last_fast = df['ema_fast'].iloc[-1]
        last_slow = df['ema_slow'].iloc[-1]
        prev_fast = df['ema_fast'].iloc[-2]
        prev_slow = df['ema_slow'].iloc[-2]
        
        # Bullish Cross
        if prev_fast <= prev_slow and last_fast > last_slow:
            return 1, self.weights['EMA_CROSS'], "EMA Bullish Cross"
        # Bearish Cross
        elif prev_fast >= prev_slow and last_fast < last_slow:
            return -1, self.weights['EMA_CROSS'], "EMA Bearish Cross"
        # Trend Continuation
        elif last_fast > last_slow and df['close'].iloc[-1] > last_fast:
            return 0.5, self.weights['EMA_CROSS'], "Strong Uptrend"
        elif last_fast < last_slow and df['close'].iloc[-1] < last_fast:
            return -0.5, self.weights['EMA_CROSS'], "Strong Downtrend"
            
        return 0, self.weights['EMA_CROSS'], "EMA Neutral"

    def _strategy_rsi(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """RSI Oversold/Overbought"""
        df = df.copy()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        current_rsi = df['rsi'].iloc[-1]
        
        if current_rsi < 30:
            return 1, self.weights['RSI_MEAN_REV'], f"RSI Oversold ({current_rsi:.1f})"
        elif current_rsi > 70:
            return -1, self.weights['RSI_MEAN_REV'], f"RSI Overbought ({current_rsi:.1f})"
        elif 45 < current_rsi < 55:
            return 0, self.weights['RSI_MEAN_REV'], "RSI Neutral Zone"
            
        return 0, self.weights['RSI_MEAN_REV'], f"RSI Normal ({current_rsi:.1f})"

    def _strategy_macd(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """MACD Histogram Momentum"""
        df = df.copy()
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['hist'] = df['macd'] - df['signal_line']
        
        current_hist = df['hist'].iloc[-1]
        prev_hist = df['hist'].iloc[-2]
        
        if prev_hist < 0 and current_hist > 0:
            return 1, self.weights['MACD_MOMENTUM'], "MACD Bullish Crossover"
        elif prev_hist > 0 and current_hist < 0:
            return -1, self.weights['MACD_MOMENTUM'], "MACD Bearish Crossover"
        elif current_hist > 0 and current_hist > prev_hist:
            return 0.5, self.weights['MACD_MOMENTUM'], "MACD Momentum Up"
        elif current_hist < 0 and current_hist < prev_hist:
            return -0.5, self.weights['MACD_MOMENTUM'], "MACD Momentum Down"
            
        return 0, self.weights['MACD_MOMENTUM'], "MACD Flat"

# Example Usage for Testing
if __name__ == "__main__":
    # Generate dummy data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(100))
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices + np.random.rand(100),
        'low': prices - np.random.rand(100),
        'close': prices
    })
    
    engine = StrategyEnsemble()
    result = engine.analyze(df)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"Regime: {result['regime']}")
