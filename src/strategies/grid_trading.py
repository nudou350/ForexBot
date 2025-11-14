"""
Grid Trading Strategy for EUR/CAD Trading Bot
Low volatility strategy with 75% target win rate
Places buy/sell orders at regular intervals in ranging markets
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config


class GridTradingStrategy:
    """
    Grid trading for EUR/CAD in ranging markets
    Places buy/sell orders at regular intervals
    """

    def __init__(self, grid_spacing_pips: int = None, num_grids: int = None,
                 total_capital: float = None):
        """
        Initialize grid trading strategy

        Args:
            grid_spacing_pips: Distance between grid levels in pips
            num_grids: Number of grid levels
            total_capital: Total capital for grid trading
        """
        self.grid_spacing_pips = grid_spacing_pips or config.GRID_SPACING_PIPS
        self.num_grids = num_grids or config.GRID_NUM_GRIDS
        self.total_capital = total_capital or config.INITIAL_CAPITAL
        self.name = "Grid Trading"
        self.pip_value = config.EURCAD_PIP_VALUE

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Grid trading doesn't use traditional signals
        Instead, check if conditions are suitable for grid

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame (not modified for grid strategy)
        """
        # Grid strategy is condition-based, not signal-based
        return df

    def is_grid_suitable(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check if current market conditions are suitable for grid trading

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (is_suitable, reason)
        """
        df = self._calculate_indicators(df)

        adx = df['ADX'].iloc[-1]
        atr = df['ATR'].iloc[-1]
        atr_avg = df['ATR'].rolling(20).mean().iloc[-1]

        # Grid works best in low volatility, ranging markets
        if adx > 30:
            return False, "ADX too high - trending market"

        if atr > atr_avg * 1.3:
            return False, "Volatility too high for grid trading"

        return True, "Conditions suitable for grid trading"

    def create_grid(self, current_price: float, atr: float) -> List[Dict]:
        """
        Create grid orders based on current price and volatility

        Args:
            current_price: Current EUR/CAD price
            atr: Current ATR value

        Returns:
            List of grid order dictionaries
        """
        # Dynamic grid spacing based on volatility
        dynamic_spacing = max(self.grid_spacing_pips, int(atr / self.pip_value * 0.5))
        spacing_price = dynamic_spacing * self.pip_value

        # Capital allocation per grid
        capital_per_grid = (self.total_capital * config.GRID_CAPITAL_ALLOCATION /
                           self.num_grids)

        grids = []

        # Buy grids below current price
        for i in range(1, self.num_grids // 2 + 1):
            buy_price = current_price - (spacing_price * i)
            sell_target = buy_price + spacing_price

            grids.append({
                'type': 'buy',
                'price': buy_price,
                'amount': capital_per_grid / buy_price,
                'take_profit': sell_target,
                'stop_loss': buy_price - (spacing_price * 2),  # 2 grids below
                'grid_level': -i
            })

        # Sell grids above current price
        for i in range(1, self.num_grids // 2 + 1):
            sell_price = current_price + (spacing_price * i)
            buy_target = sell_price - spacing_price

            grids.append({
                'type': 'sell',
                'price': sell_price,
                'amount': capital_per_grid / sell_price,
                'take_profit': buy_target,
                'stop_loss': sell_price + (spacing_price * 2),  # 2 grids above
                'grid_level': i
            })

        return grids

    def should_exit_grid(self, df: pd.DataFrame, grid_range: Dict) -> Tuple[bool, str]:
        """
        Determine if we should exit all grid orders

        Args:
            df: DataFrame with OHLCV data
            grid_range: Dictionary with 'top' and 'bottom' price levels

        Returns:
            Tuple of (should_exit, reason)
        """
        df = self._calculate_indicators(df)

        current_price = df['close'].iloc[-1]
        atr = df['ATR'].iloc[-1]
        adx = df['ADX'].iloc[-1]

        # Exit if strong trend forming
        if adx > 30:
            return True, "Strong trend detected - exiting grid"

        # Exit if price breaks grid range
        range_top = grid_range['top']
        range_bottom = grid_range['bottom']

        if current_price > range_top + (2 * atr):
            return True, "Price broke above grid range"

        if current_price < range_bottom - (2 * atr):
            return True, "Price broke below grid range"

        return False, "Grid still valid"

    def calculate_grid_range(self, df: pd.DataFrame,
                            lookback: int = 100) -> Optional[Dict]:
        """
        Calculate optimal grid range based on recent price action

        Args:
            df: DataFrame with OHLCV data
            lookback: Number of bars to analyze

        Returns:
            Dictionary with range top and bottom or None
        """
        if len(df) < lookback:
            return None

        recent_data = df.tail(lookback)

        # Use recent high/low with some buffer
        range_high = recent_data['high'].max()
        range_low = recent_data['low'].min()

        # Add buffer (0.5% on each side)
        buffer = (range_high - range_low) * 0.05
        range_top = range_high + buffer
        range_bottom = range_low - buffer

        return {
            'top': range_top,
            'bottom': range_bottom,
            'range_size': range_top - range_bottom,
            'midpoint': (range_top + range_bottom) / 2
        }

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators needed for grid trading decisions"""
        df = df.copy()

        # ADX for trend detection
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
        plus_di = 100 * (plus_dm.rolling(config.ADX_PERIOD).mean() /
                        atr.replace(0, np.nan))
        minus_di = 100 * (minus_dm.rolling(config.ADX_PERIOD).mean() /
                         atr.replace(0, np.nan))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        df['ADX'] = dx.rolling(config.ADX_PERIOD).mean()

        # ATR for volatility
        df['ATR'] = tr.rolling(config.ATR_PERIOD).mean()

        return df

    def calculate_entry_exit(self, df: pd.DataFrame, signal_type: str) -> Optional[Dict]:
        """
        Grid trading doesn't use this method
        Use create_grid() instead

        Args:
            df: DataFrame with OHLCV data
            signal_type: Not used for grid trading

        Returns:
            None (not applicable for grid strategy)
        """
        return None
