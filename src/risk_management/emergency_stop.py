"""
Emergency Stop System for EUR/CAD Trading Bot
Monitors market conditions and bot health for emergency situations
"""

import logging
from datetime import datetime
from typing import Tuple, Optional, Dict
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config


class EmergencyStopSystem:
    """
    Multiple emergency stop triggers
    Monitors market conditions and bot health
    """

    def __init__(self, risk_manager):
        """
        Initialize emergency stop system

        Args:
            risk_manager: RiskManager instance
        """
        self.risk_manager = risk_manager
        self.last_api_check: Optional[datetime] = None
        self.api_error_count = 0
        self.last_price_update: Optional[datetime] = None
        self.logger = logging.getLogger(__name__)

    def check_emergency_conditions(self, df: pd.DataFrame,
                                   current_time: datetime) -> Tuple[bool, Optional[str]]:
        """
        Check all emergency stop conditions

        Args:
            df: DataFrame with market data
            current_time: Current timestamp

        Returns:
            Tuple of (should_stop, reason)
        """
        # 1. Excessive drawdown
        if self.risk_manager.current_drawdown >= config.HALT_ON_DRAWDOWN:
            return True, f"Drawdown exceeded {config.HALT_ON_DRAWDOWN*100}%"

        # 2. Market volatility spike
        if len(df) >= 50:
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else None
            if current_atr is not None:
                avg_atr = df['ATR'].rolling(50).mean().iloc[-1]
                if current_atr > avg_atr * 2:
                    return True, "Extreme volatility detected"

        # 3. API connectivity issues
        if self.api_error_count >= 3:
            return True, "Multiple API errors detected"

        # 4. Stale price data
        if self.last_price_update:
            time_since_update = (current_time - self.last_price_update).seconds
            if time_since_update > 300:  # 5 minutes
                return True, "Stale price data - possible connection issue"

        # 5. Unexpected price gap
        if len(df) >= 2:
            price_change = (abs(df['close'].iloc[-1] - df['close'].iloc[-2]) /
                          df['close'].iloc[-2])
            if price_change > 0.02:  # 2% gap
                return True, "Unexpected price gap detected"

        # 6. Weekend gap protection
        if current_time.weekday() in [5, 6]:  # Saturday, Sunday
            return True, "Weekend - market closed"

        # 7. Major news event protection (basic time-based check)
        if self.is_major_news_time(current_time):
            return True, "Major news event - staying out"

        return False, None

    def is_major_news_time(self, current_time: datetime) -> bool:
        """
        Check if current time is within major news event window

        Args:
            current_time: Current timestamp

        Returns:
            True if within news event window
        """
        # Avoid first Friday of month (employment data)
        if current_time.weekday() == 4 and current_time.day <= 7:
            hour = current_time.hour
            if 8 <= hour <= 10:  # 8:30 AM EST typical release time
                self.logger.warning("Potential major news event time - avoiding trading")
                return True

        return False

    def log_api_error(self) -> None:
        """Log API error and check if threshold reached"""
        self.api_error_count += 1
        self.logger.error(f"API error logged. Total errors: {self.api_error_count}")

        if self.api_error_count >= 3:
            self.risk_manager.halt_trading("Multiple API errors")

    def reset_api_errors(self) -> None:
        """Reset API error counter (after successful requests)"""
        if self.api_error_count > 0:
            self.logger.info(f"Resetting API error count from {self.api_error_count}")
        self.api_error_count = 0

    def update_price_timestamp(self, timestamp: datetime) -> None:
        """
        Update last price update timestamp

        Args:
            timestamp: Timestamp of last price update
        """
        self.last_price_update = timestamp

    def check_trading_hours(self, current_time: datetime) -> Tuple[bool, str]:
        """
        Check if current time is within trading hours

        Args:
            current_time: Current timestamp

        Returns:
            Tuple of (is_trading_hours, reason)
        """
        # Check weekend
        if config.AVOID_TRADING_WEEKENDS and current_time.weekday() in [5, 6]:
            return False, "Weekend - market closed"

        # Check trading hours (GMT/UTC)
        hour = current_time.hour
        if hour < config.TRADING_START_HOUR or hour >= config.TRADING_END_HOUR:
            return False, f"Outside trading hours ({config.TRADING_START_HOUR}-{config.TRADING_END_HOUR} GMT)"

        return True, "Within trading hours"

    def check_spread_conditions(self, bid: float, ask: float) -> Tuple[bool, str]:
        """
        Check if spread is within acceptable range

        Args:
            bid: Current bid price
            ask: Current ask price

        Returns:
            Tuple of (is_acceptable, reason)
        """
        if bid <= 0 or ask <= 0:
            return False, "Invalid bid/ask prices"

        spread_pips = (ask - bid) / config.EURCAD_PIP_VALUE

        # Normal spread is 0.4-0.6 pips, halt if >10 pips
        if spread_pips > 10:
            return False, f"Excessive spread: {spread_pips:.1f} pips"

        if spread_pips > 3:
            self.logger.warning(f"Wide spread detected: {spread_pips:.1f} pips")

        return True, "Spread acceptable"

    def get_system_health(self) -> Dict:
        """
        Get system health status

        Returns:
            Dictionary with health metrics
        """
        return {
            'api_error_count': self.api_error_count,
            'last_price_update': self.last_price_update,
            'time_since_last_update': (
                (datetime.now() - self.last_price_update).seconds
                if self.last_price_update else None
            ),
            'trading_halted': self.risk_manager.trading_halted,
            'halt_reason': self.risk_manager.halt_reason
        }
