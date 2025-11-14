"""
Risk Manager for EUR/CAD Trading Bot
Implements multi-layer risk protection and position sizing
"""

import logging
from typing import Tuple, List, Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config


class RiskManager:
    """
    Comprehensive risk management system for EUR/CAD bot
    Implements multiple layers of protection
    """

    def __init__(self, initial_capital: float,
                 max_risk_per_trade: float = None):
        """
        Initialize risk manager

        Args:
            initial_capital: Starting capital
            max_risk_per_trade: Maximum risk per trade as decimal (e.g., 0.01 for 1%)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_risk_per_trade = max_risk_per_trade or config.MAX_RISK_PER_TRADE
        self.max_drawdown = config.MAX_DRAWDOWN
        self.max_daily_loss = config.MAX_DAILY_LOSS
        self.max_concurrent_trades = config.MAX_CONCURRENT_TRADES

        # Tracking
        self.open_positions: List[Dict] = []
        self.daily_pnl = 0.0
        self.peak_capital = initial_capital
        self.current_drawdown = 0.0
        self.consecutive_losses = 0
        self.daily_trade_count = 0

        # Circuit breakers
        self.trading_halted = False
        self.halt_reason: Optional[str] = None

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def can_open_position(self, risk_amount: float,
                         strategy_name: str) -> Tuple[bool, str]:
        """
        Check if new position is allowed based on all risk rules

        Args:
            risk_amount: Dollar amount at risk
            strategy_name: Name of strategy requesting position

        Returns:
            Tuple of (can_open, reason)
        """
        # Check if trading is halted
        if self.trading_halted:
            return False, f"Trading halted: {self.halt_reason}"

        # Check per-trade risk
        if risk_amount > self.current_capital * self.max_risk_per_trade:
            return False, "Exceeds per-trade risk limit"

        # Check daily loss limit
        if self.daily_pnl < -(self.current_capital * self.max_daily_loss):
            self.halt_trading("Daily loss limit reached")
            return False, "Daily loss limit reached"

        # Check drawdown
        self.current_drawdown = ((self.peak_capital - self.current_capital) /
                                 self.peak_capital)
        if self.current_drawdown >= self.max_drawdown:
            self.halt_trading("Maximum drawdown reached")
            return False, "Maximum drawdown reached"

        # Check concurrent positions
        if len(self.open_positions) >= self.max_concurrent_trades:
            return False, "Maximum concurrent trades reached"

        # Check consecutive losses
        if self.consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
            self.halt_trading("5 consecutive losses - cooldown period")
            return False, "Too many consecutive losses"

        # Check total portfolio risk
        total_risk = sum([pos['risk_amount'] for pos in self.open_positions])
        if total_risk + risk_amount > self.current_capital * config.MAX_TOTAL_PORTFOLIO_RISK:
            return False, "Total portfolio risk exceeds limit"

        # Check daily trade limit (prevent overtrading)
        if self.daily_trade_count >= config.MAX_DAILY_TRADES:
            return False, "Daily trade limit reached"

        return True, "Position allowed"

    def calculate_position_size(self, entry_price: float, stop_loss_price: float,
                               risk_percentage: float) -> float:
        """
        Calculate optimal position size based on risk

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            risk_percentage: Risk as decimal (e.g., 0.01 for 1%)

        Returns:
            Position size in lots (1 lot = 100,000 units)
        """
        risk_amount = self.current_capital * risk_percentage
        price_risk_pips = abs(entry_price - stop_loss_price) / config.EURCAD_PIP_VALUE

        if price_risk_pips == 0:
            return 0.0

        # EUR/CAD: 1 standard lot = 100,000 units
        # 1 pip = 0.0001 = $10 per standard lot (for USD account)
        pip_value = 10.0  # Adjust based on account currency

        position_risk_per_pip = risk_amount / price_risk_pips
        lots = position_risk_per_pip / pip_value

        # Limit position to 10% of capital
        max_notional = self.current_capital * 0.10
        max_lots = max_notional / (entry_price * 100000)

        return min(lots, max_lots)

    def add_position(self, position: Dict) -> None:
        """
        Add new position to tracking

        Args:
            position: Position dictionary with details
        """
        self.open_positions.append(position)
        self.daily_trade_count += 1
        self.logger.info(f"Position added: {position['type']} {position.get('size', 0)} lots")

    def close_position(self, position_id: int, pnl: float) -> None:
        """
        Close position and update tracking

        Args:
            position_id: Position ID to close
            pnl: Profit/loss for the position
        """
        # Remove from open positions
        self.open_positions = [p for p in self.open_positions
                              if p.get('id') != position_id]

        # Update capital
        self.current_capital += pnl
        self.daily_pnl += pnl

        # Update peak capital
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

        # Track consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
            self.logger.warning(f"Loss recorded. Consecutive losses: {self.consecutive_losses}")
        else:
            self.consecutive_losses = 0
            self.logger.info(f"Profit recorded: ${pnl:.2f}")

        self.logger.info(f"Position closed. P&L: ${pnl:.2f}, Capital: ${self.current_capital:.2f}")

    def halt_trading(self, reason: str) -> None:
        """
        Emergency stop - halt all trading

        Args:
            reason: Reason for halting
        """
        self.trading_halted = True
        self.halt_reason = reason
        self.logger.critical(f"TRADING HALTED: {reason}")
        self.send_alert(f"Trading halted: {reason}")

    def resume_trading(self) -> None:
        """Resume trading after manual review"""
        self.trading_halted = False
        self.halt_reason = None
        self.consecutive_losses = 0
        self.logger.info("Trading resumed")

    def reset_daily_metrics(self) -> None:
        """Reset daily metrics (call at start of each day)"""
        self.daily_pnl = 0.0
        self.daily_trade_count = 0
        self.logger.info("Daily metrics reset")

    def send_alert(self, message: str) -> None:
        """
        Send alert via configured channels

        Args:
            message: Alert message
        """
        # TODO: Implement Telegram/Email/SMS alerts
        self.logger.critical(f"ALERT: {message}")
        print(f"\n{'='*50}")
        print(f"ALERT: {message}")
        print(f"{'='*50}\n")

    def get_account_summary(self) -> Dict:
        """
        Get current account summary

        Returns:
            Dictionary with account metrics
        """
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'daily_pnl': self.daily_pnl,
            'total_return': ((self.current_capital - self.initial_capital) /
                           self.initial_capital),
            'current_drawdown': self.current_drawdown,
            'open_positions': len(self.open_positions),
            'consecutive_losses': self.consecutive_losses,
            'daily_trade_count': self.daily_trade_count,
            'trading_halted': self.trading_halted
        }

    def get_risk_metrics(self) -> Dict:
        """
        Get risk-related metrics

        Returns:
            Dictionary with risk metrics
        """
        total_risk = sum([pos.get('risk_amount', 0) for pos in self.open_positions])

        return {
            'total_portfolio_risk': total_risk,
            'total_portfolio_risk_pct': (total_risk / self.current_capital
                                         if self.current_capital > 0 else 0),
            'available_risk': (self.current_capital * config.MAX_TOTAL_PORTFOLIO_RISK -
                             total_risk),
            'max_position_risk': self.current_capital * self.max_risk_per_trade,
            'daily_loss_limit': self.current_capital * self.max_daily_loss,
            'daily_loss_remaining': (self.current_capital * self.max_daily_loss +
                                    self.daily_pnl)
        }
