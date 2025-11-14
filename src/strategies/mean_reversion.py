"""
Mean Reversion Strategy for EUR/CAD Trading Bot
Primary strategy with 70% target win rate
Uses Bollinger Bands + RSI + MACD + Volume confluence
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config


class MeanReversionStrategy:
    """
    Optimized mean reversion for EUR/CAD ranging markets
    Enters at extremes, exits at mean
    """

    def __init__(self, risk_per_trade: float = None):
        """
        Initialize mean reversion strategy

        Args:
            risk_per_trade: Risk percentage per trade (default from config)
        """
        self.risk_per_trade = risk_per_trade or config.MEAN_REVERSION_RISK
        self.name = "Mean Reversion"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy/sell signals for mean reversion

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with signal columns added
        """
        df = df.copy()

        # Calculate indicators
        df = self._calculate_indicators(df)

        # Entry conditions (strict confluence required)
        df['long_signal'] = (
            # Price conditions - at lower Bollinger Band
            (df['close'] <= df['BB_lower']) &
            (df['close'] < df['EMA_20']) &

            # Momentum conditions - oversold but showing reversal
            (df['RSI'] < config.RSI_OVERSOLD) &
            (df['MACD_histogram'] < 0) &
            (df['MACD_histogram'] > df['MACD_histogram'].shift(1)) &  # Divergence

            # Volume confirmation - increase on reversal
            (df['volume'] > df['volume_ma'] * 1.3) &

            # Trend filter - don't fight strong trends
            (df['ADX'] < 35) &

            # Avoid high volatility (news events)
            (df['ATR'] < df['ATR_ma'] * 1.5)
        )

        df['short_signal'] = (
            # Price conditions - at upper Bollinger Band
            (df['close'] >= df['BB_upper']) &
            (df['close'] > df['EMA_20']) &

            # Momentum conditions - overbought but showing reversal
            (df['RSI'] > config.RSI_OVERBOUGHT) &
            (df['MACD_histogram'] > 0) &
            (df['MACD_histogram'] < df['MACD_histogram'].shift(1)) &  # Divergence

            # Volume confirmation
            (df['volume'] > df['volume_ma'] * 1.3) &

            # Trend filter
            (df['ADX'] < 35) &

            # Avoid high volatility
            (df['ATR'] < df['ATR_ma'] * 1.5)
        )

        return df

    def calculate_entry_exit(self, df: pd.DataFrame, signal_type: str) -> Optional[Dict]:
        """
        Calculate entry price, stop loss, and take profit levels

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
        bb_middle = df['BB_middle'].iloc[-1]
        bb_upper = df['BB_upper'].iloc[-1]
        bb_lower = df['BB_lower'].iloc[-1]

        if signal_type == 'long':
            entry = current_price
            stop_loss = entry - (config.STOP_LOSS_ATR_MULTIPLE * atr)
            take_profit_1 = bb_middle  # First target: BB middle
            take_profit_2 = bb_upper  # Second target: BB upper

        elif signal_type == 'short':
            entry = current_price
            stop_loss = entry + (config.STOP_LOSS_ATR_MULTIPLE * atr)
            take_profit_1 = bb_middle
            take_profit_2 = bb_lower

        else:
            return None

        # Calculate risk/reward ratios
        risk = abs(entry - stop_loss)
        reward_1 = abs(take_profit_1 - entry)
        reward_2 = abs(take_profit_2 - entry)

        # Only take trades with minimum 1.5:1 R/R
        if risk == 0 or reward_1 / risk < 1.5:
            return None

        return {
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,  # Close 50% here
            'take_profit_2': take_profit_2,  # Close remaining 50% here
            'risk_reward_1': reward_1 / risk if risk > 0 else 0,
            'risk_reward_2': reward_2 / risk if risk > 0 else 0
        }

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        df = df.copy()

        # Bollinger Bands (20, 2)
        df['BB_middle'] = df['close'].rolling(config.BB_PERIOD).mean()
        df['BB_std'] = df['close'].rolling(config.BB_PERIOD).std()
        df['BB_upper'] = df['BB_middle'] + (df['BB_std'] * config.BB_STD)
        df['BB_lower'] = df['BB_middle'] - (df['BB_std'] * config.BB_STD)

        # RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(config.RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(config.RSI_PERIOD).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema_12 = df['close'].ewm(span=config.MACD_FAST, adjust=False).mean()
        ema_26 = df['close'].ewm(span=config.MACD_SLOW, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26
        df['MACD_signal'] = df['MACD'].ewm(span=config.MACD_SIGNAL, adjust=False).mean()
        df['MACD_histogram'] = df['MACD'] - df['MACD_signal']

        # Volume
        df['volume_ma'] = df['volume'].rolling(20).mean()

        # ATR (14)
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['ATR'] = ranges.max(axis=1).rolling(config.ATR_PERIOD).mean()
        df['ATR_ma'] = df['ATR'].rolling(20).mean()

        # EMA for trend filter
        df['EMA_20'] = df['close'].ewm(span=config.EMA_FAST, adjust=False).mean()

        # ADX (from regime detector logic)
        df = self._calculate_adx(df, config.ADX_PERIOD)

        return df

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Calculate ADX for trend strength filtering"""
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()

        plus_di = 100 * (plus_dm.rolling(period).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr.replace(0, np.nan))

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        df['ADX'] = dx.rolling(period).mean()

        return df
