"""
Trend Following Strategy for EUR/CAD Trading Bot
Secondary strategy with 65% target win rate
Enters on pullbacks during strong trends with trailing stops
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config


class TrendFollowingStrategy:
    """
    Trend following for EUR/CAD during strong trends
    Enters on pullbacks with trailing stops for trend continuation
    """

    def __init__(self, risk_per_trade: float = None):
        """
        Initialize trend following strategy

        Args:
            risk_per_trade: Risk percentage per trade (default from config)
        """
        self.risk_per_trade = risk_per_trade or config.TREND_FOLLOWING_RISK
        self.name = "Trend Following"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trend following signals with strict trend confirmation

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with signal columns added
        """
        df = df.copy()

        # Calculate indicators
        df = self._calculate_indicators(df)

        # Long signals (uptrend with pullback)
        df['long_signal'] = (
            # Strong uptrend confirmed
            (df['EMA_20'] > df['EMA_50']) &
            (df['EMA_50'] > df['EMA_200']) &
            (df['ADX'] > 25) &  # Strong trend

            # Pullback to support (within 0.5% of EMA20)
            (df['close'] <= df['EMA_20'] * 1.005) &
            (df['close'] > df['EMA_50']) &  # Still above EMA50

            # Momentum confirmation
            (df['RSI'] > 45) & (df['RSI'] < 65) &  # Not oversold, still has room
            (df['MACD'] > df['MACD_signal']) &  # MACD bullish

            # Volume increase on bounce
            (df['volume'] > df['volume_ma'] * 1.1)
        )

        # Short signals (downtrend with pullback)
        df['short_signal'] = (
            # Strong downtrend confirmed
            (df['EMA_20'] < df['EMA_50']) &
            (df['EMA_50'] < df['EMA_200']) &
            (df['ADX'] > 25) &

            # Pullback to resistance (within 0.5% of EMA20)
            (df['close'] >= df['EMA_20'] * 0.995) &
            (df['close'] < df['EMA_50']) &

            # Momentum confirmation
            (df['RSI'] > 35) & (df['RSI'] < 55) &
            (df['MACD'] < df['MACD_signal']) &

            # Volume increase
            (df['volume'] > df['volume_ma'] * 1.1)
        )

        return df

    def calculate_entry_exit(self, df: pd.DataFrame, signal_type: str) -> Optional[Dict]:
        """
        Calculate entry with wider stops and trailing mechanism

        Args:
            df: DataFrame with calculated indicators
            signal_type: 'long' or 'short'

        Returns:
            Dictionary with entry/exit levels or None
        """
        if len(df) < 1:
            return None

        current_price = df['close'].iloc[-1]
        atr = df['ATR'].iloc[-1]

        if signal_type == 'long':
            entry = current_price
            stop_loss = entry - (2.5 * atr)  # Wider stop for trends
            take_profit_1 = entry + (2 * atr)  # 1:1.6 R:R
            take_profit_2 = entry + (4 * atr)  # 1:3.2 R:R
            trailing_stop_distance = config.TRAILING_STOP_ATR_MULTIPLE * atr

        elif signal_type == 'short':
            entry = current_price
            stop_loss = entry + (2.5 * atr)
            take_profit_1 = entry - (2 * atr)
            take_profit_2 = entry - (4 * atr)
            trailing_stop_distance = config.TRAILING_STOP_ATR_MULTIPLE * atr

        else:
            return None

        # Calculate risk/reward
        risk = abs(entry - stop_loss)
        reward_1 = abs(take_profit_1 - entry)
        reward_2 = abs(take_profit_2 - entry)

        # Only take trades with minimum 1.5:1 R/R
        if risk == 0 or reward_1 / risk < 1.5:
            return None

        return {
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,  # Close 30% here
            'take_profit_2': take_profit_2,  # Keep 70% for trend continuation
            'trailing_stop_distance': trailing_stop_distance,
            'move_to_breakeven_at': take_profit_1,  # Move SL to BE at TP1
            'risk_reward_1': reward_1 / risk if risk > 0 else 0,
            'risk_reward_2': reward_2 / risk if risk > 0 else 0
        }

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate trend indicators"""
        df = df.copy()

        # EMAs
        df['EMA_20'] = df['close'].ewm(span=config.EMA_FAST, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=config.EMA_MEDIUM, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=config.EMA_SLOW, adjust=False).mean()

        # ADX
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)

        atr = tr.rolling(config.ADX_PERIOD).mean()
        plus_di = 100 * (plus_dm.rolling(config.ADX_PERIOD).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (minus_dm.rolling(config.ADX_PERIOD).mean() / atr.replace(0, np.nan))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        df['ADX'] = dx.rolling(config.ADX_PERIOD).mean()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(config.RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(config.RSI_PERIOD).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        ema_12 = df['close'].ewm(span=config.MACD_FAST, adjust=False).mean()
        ema_26 = df['close'].ewm(span=config.MACD_SLOW, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26
        df['MACD_signal'] = df['MACD'].ewm(span=config.MACD_SIGNAL, adjust=False).mean()

        # Volume
        df['volume_ma'] = df['volume'].rolling(20).mean()

        # ATR
        df['ATR'] = tr.rolling(config.ATR_PERIOD).mean()

        return df
