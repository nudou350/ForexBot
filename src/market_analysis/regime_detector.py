"""
Market Regime Detection for EUR/CAD Trading Bot
Analyzes market conditions to select optimal strategy
"""

import pandas as pd
import numpy as np
from typing import Literal
import sys
import os

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config

RegimeType = Literal['STRONG_TREND', 'WEAK_TREND', 'RANGING', 'BREAKOUT_PENDING',
                     'HIGH_VOLATILITY', 'LOW_VOLATILITY']


class MarketRegimeDetector:
    """
    Detect current market regime for EUR/CAD
    Uses multiple indicators to classify market state
    """

    def __init__(self, lookback: int = 100):
        """
        Initialize regime detector

        Args:
            lookback: Number of bars to analyze for regime detection
        """
        self.lookback = lookback

    def detect_regime(self, df: pd.DataFrame) -> RegimeType:
        """
        Analyze multiple indicators to determine market regime

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Regime type as string
        """
        # Calculate indicators
        df = self._calculate_indicators(df)

        # Get latest values
        adx = df['ADX'].iloc[-1]
        atr = df['ATR'].iloc[-1]
        atr_avg = df['ATR'].rolling(20).mean().iloc[-1]
        bb_width = df['BB_width'].iloc[-1]
        bb_width_avg = df['BB_width'].rolling(50).mean().iloc[-1]

        # Check trend alignment
        ema_aligned_up = (df['EMA_20'].iloc[-1] > df['EMA_50'].iloc[-1] >
                          df['EMA_200'].iloc[-1])
        ema_aligned_down = (df['EMA_20'].iloc[-1] < df['EMA_50'].iloc[-1] <
                            df['EMA_200'].iloc[-1])

        # Regime classification logic
        if adx > config.ADX_STRONG_TREND_THRESHOLD and (ema_aligned_up or ema_aligned_down):
            return 'STRONG_TREND'

        elif adx > config.ADX_WEAK_TREND_THRESHOLD and (ema_aligned_up or ema_aligned_down):
            return 'WEAK_TREND'

        elif (bb_width < bb_width_avg * config.BB_WIDTH_BREAKOUT_MULTIPLIER and
              atr < atr_avg * config.ATR_LOW_VOLATILITY_MULTIPLIER):
            return 'BREAKOUT_PENDING'

        elif atr > atr_avg * config.ATR_HIGH_VOLATILITY_MULTIPLIER:
            return 'HIGH_VOLATILITY'

        elif bb_width < bb_width_avg * config.BB_WIDTH_LOW_VOL_MULTIPLIER:
            return 'LOW_VOLATILITY'

        else:
            return 'RANGING'

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all necessary indicators for regime detection"""
        df = df.copy()

        # EMAs
        df['EMA_20'] = df['close'].ewm(span=config.EMA_FAST, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=config.EMA_MEDIUM, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=config.EMA_SLOW, adjust=False).mean()

        # ADX
        df = self._calculate_adx(df, config.ADX_PERIOD)

        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['ATR'] = ranges.max(axis=1).rolling(config.ATR_PERIOD).mean()

        # Bollinger Bands Width
        df['BB_middle'] = df['close'].rolling(config.BB_PERIOD).mean()
        df['BB_std'] = df['close'].rolling(config.BB_PERIOD).std()
        df['BB_upper'] = df['BB_middle'] + (df['BB_std'] * config.BB_STD)
        df['BB_lower'] = df['BB_middle'] - (df['BB_std'] * config.BB_STD)
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']

        return df

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Average Directional Index

        Args:
            df: DataFrame with OHLC data
            period: ADX calculation period

        Returns:
            DataFrame with ADX column added
        """
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

        # Avoid division by zero
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr.replace(0, np.nan))

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        df['ADX'] = dx.rolling(period).mean()

        return df

    def get_regime_description(self, regime: RegimeType) -> str:
        """
        Get human-readable description of regime

        Args:
            regime: Regime type

        Returns:
            Description string
        """
        descriptions = {
            'STRONG_TREND': 'Strong directional trend with high ADX and aligned EMAs',
            'WEAK_TREND': 'Moderate trend with some directional bias',
            'RANGING': 'Sideways market with no clear direction',
            'BREAKOUT_PENDING': 'Low volatility consolidation - potential breakout',
            'HIGH_VOLATILITY': 'Elevated volatility - caution advised',
            'LOW_VOLATILITY': 'Very low volatility - good for grid trading'
        }
        return descriptions.get(regime, 'Unknown regime')
