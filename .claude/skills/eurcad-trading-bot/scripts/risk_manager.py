"""
Risk Manager for EUR/CAD Trading Bot
Handles position sizing, risk calculations, and account protection
"""

import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass


@dataclass
class TradeRisk:
    """Data class for trade risk parameters"""
    position_size: int  # Position size in units
    stop_loss_pips: float  # Stop loss in pips
    stop_loss_price: float  # Stop loss price level
    risk_amount: float  # Dollar risk amount
    risk_percent: float  # Risk as percentage of account
    take_profit_price: Optional[float] = None
    reward_risk_ratio: Optional[float] = None


class RiskManager:
    """
    Comprehensive risk management system
    Enforces position sizing, daily limits, and account protection
    """

    def __init__(
        self,
        account_balance: float,
        max_risk_per_trade: float = 0.02,  # 2%
        max_daily_risk: float = 0.05,  # 5%
        max_total_exposure: float = 0.06,  # 6%
        max_positions: int = 3,
        max_trades_per_day: int = 5,
        max_consecutive_losses: int = 3
    ):
        """
        Initialize risk manager

        Args:
            account_balance: Current account equity
            max_risk_per_trade: Maximum risk per trade (decimal, e.g., 0.02 = 2%)
            max_daily_risk: Maximum daily risk/loss (decimal)
            max_total_exposure: Maximum total open exposure (decimal)
            max_positions: Maximum number of simultaneous positions
            max_trades_per_day: Maximum trades allowed per day
            max_consecutive_losses: Max consecutive losses before stopping
        """
        self.account_balance = account_balance
        self.starting_balance = account_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_risk = max_daily_risk
        self.max_total_exposure = max_total_exposure
        self.max_positions = max_positions
        self.max_trades_per_day = max_trades_per_day
        self.max_consecutive_losses = max_consecutive_losses

        # Trading state
        self.open_positions = []
        self.daily_trades = {}  # date -> count
        self.daily_pnl = {}  # date -> pnl
        self.consecutive_losses = 0
        self.trading_allowed = True

        # Constants
        self.pip_value_per_lot = 10  # $10 per pip for standard lot
        self.pip_size = 0.0001

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        risk_percent: Optional[float] = None
    ) -> TradeRisk:
        """
        Calculate position size based on risk parameters

        Args:
            entry_price: Planned entry price
            stop_loss_price: Planned stop loss price
            risk_percent: Override default risk percent (optional)

        Returns:
            TradeRisk object with position sizing details
        """
        if risk_percent is None:
            risk_percent = self.max_risk_per_trade

        # Calculate risk amount in dollars
        risk_amount = self.account_balance * risk_percent

        # Calculate stop loss in pips
        stop_loss_pips = abs(entry_price - stop_loss_price) / self.pip_size

        # Calculate position size
        # Risk = Position Size × Pip Value × Stop Loss in Pips
        # Position Size = Risk / (Pip Value × Stop Loss in Pips)

        # First, calculate for 1 standard lot (100,000 units)
        risk_per_lot = self.pip_value_per_lot * stop_loss_pips

        # Calculate number of lots
        lots = risk_amount / risk_per_lot

        # Convert to units (1 lot = 100,000 units)
        position_size = int(lots * 100000)

        # Round to nearest 1000 units (0.01 lot)
        position_size = round(position_size / 1000) * 1000

        # Ensure minimum position (1000 units = 0.01 lot)
        position_size = max(position_size, 1000)

        # Calculate actual risk with rounded position
        actual_lots = position_size / 100000
        actual_risk_amount = actual_lots * risk_per_lot
        actual_risk_percent = actual_risk_amount / self.account_balance

        return TradeRisk(
            position_size=position_size,
            stop_loss_pips=stop_loss_pips,
            stop_loss_price=stop_loss_price,
            risk_amount=actual_risk_amount,
            risk_percent=actual_risk_percent
        )

    def calculate_volatility_adjusted_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        current_atr: float,
        normal_atr: float
    ) -> TradeRisk:
        """
        Calculate position size adjusted for current volatility

        Args:
            entry_price: Planned entry price
            stop_loss_price: Planned stop loss price
            current_atr: Current ATR value
            normal_atr: Normal/average ATR value

        Returns:
            TradeRisk object with volatility-adjusted sizing
        """
        # Calculate base position size
        base_risk = self.calculate_position_size(entry_price, stop_loss_price)

        # Adjust for volatility
        # If ATR is higher than normal, reduce position size
        # If ATR is lower than normal, can increase (but capped)
        volatility_ratio = normal_atr / current_atr
        volatility_ratio = max(0.5, min(volatility_ratio, 1.5))  # Limit adjustment

        adjusted_size = int(base_risk.position_size * volatility_ratio)
        adjusted_size = round(adjusted_size / 1000) * 1000  # Round to 1000

        # Recalculate risk with adjusted size
        actual_lots = adjusted_size / 100000
        stop_loss_pips = abs(entry_price - stop_loss_price) / self.pip_size
        risk_amount = actual_lots * self.pip_value_per_lot * stop_loss_pips

        return TradeRisk(
            position_size=adjusted_size,
            stop_loss_pips=stop_loss_pips,
            stop_loss_price=stop_loss_price,
            risk_amount=risk_amount,
            risk_percent=risk_amount / self.account_balance
        )

    def can_open_position(self, new_position_risk: TradeRisk) -> Tuple[bool, str]:
        """
        Check if new position can be opened based on risk rules

        Args:
            new_position_risk: Risk parameters for new position

        Returns:
            Tuple (can_open: bool, reason: str)
        """
        today = date.today()

        # Check if trading is allowed
        if not self.trading_allowed:
            return (False, "Trading is disabled (circuit breaker triggered)")

        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return (False, f"Max consecutive losses reached ({self.consecutive_losses})")

        # Check daily trade limit
        today_trades = self.daily_trades.get(today, 0)
        if today_trades >= self.max_trades_per_day:
            return (False, f"Daily trade limit reached ({today_trades}/{self.max_trades_per_day})")

        # Check daily loss limit
        today_pnl = self.daily_pnl.get(today, 0)
        max_daily_loss = self.account_balance * self.max_daily_risk

        if today_pnl <= -max_daily_loss:
            return (False, f"Daily loss limit reached (${abs(today_pnl):.2f})")

        # Check maximum positions
        if len(self.open_positions) >= self.max_positions:
            return (False, f"Maximum positions reached ({len(self.open_positions)}/{self.max_positions})")

        # Check total exposure
        current_exposure = sum(pos['risk_amount'] for pos in self.open_positions)
        total_exposure = current_exposure + new_position_risk.risk_amount
        max_exposure = self.account_balance * self.max_total_exposure

        if total_exposure > max_exposure:
            return (False, f"Total exposure would exceed limit (${total_exposure:.2f} > ${max_exposure:.2f})")

        # Check individual trade risk
        if new_position_risk.risk_percent > self.max_risk_per_trade:
            return (False, f"Trade risk too high ({new_position_risk.risk_percent*100:.1f}% > {self.max_risk_per_trade*100:.1f}%)")

        # All checks passed
        return (True, "Position approved")

    def register_trade(self, trade_risk: TradeRisk, trade_id: str):
        """
        Register new trade in risk manager

        Args:
            trade_risk: Risk parameters for the trade
            trade_id: Unique identifier for trade
        """
        today = date.today()

        # Add to open positions
        self.open_positions.append({
            'trade_id': trade_id,
            'risk_amount': trade_risk.risk_amount,
            'position_size': trade_risk.position_size,
            'timestamp': datetime.now()
        })

        # Update daily trade count
        self.daily_trades[today] = self.daily_trades.get(today, 0) + 1

        print(f"✓ Trade {trade_id} registered")
        print(f"  Risk: ${trade_risk.risk_amount:.2f} ({trade_risk.risk_percent*100:.2f}%)")
        print(f"  Open positions: {len(self.open_positions)}")

    def close_trade(
        self,
        trade_id: str,
        pnl: float,
        is_winner: bool
    ):
        """
        Close trade and update risk tracking

        Args:
            trade_id: Trade identifier
            pnl: Profit/loss amount
            is_winner: True if profitable trade
        """
        today = date.today()

        # Remove from open positions
        self.open_positions = [
            pos for pos in self.open_positions
            if pos['trade_id'] != trade_id
        ]

        # Update daily P&L
        self.daily_pnl[today] = self.daily_pnl.get(today, 0) + pnl

        # Update account balance
        self.account_balance += pnl

        # Update consecutive losses
        if is_winner:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

        # Check circuit breaker
        self._check_circuit_breaker()

        print(f"✓ Trade {trade_id} closed")
        print(f"  P&L: ${pnl:.2f}")
        print(f"  New balance: ${self.account_balance:.2f}")
        print(f"  Daily P&L: ${self.daily_pnl[today]:.2f}")
        print(f"  Consecutive losses: {self.consecutive_losses}")

    def _check_circuit_breaker(self):
        """Check if circuit breaker should be triggered"""
        today = date.today()
        today_pnl = self.daily_pnl.get(today, 0)
        max_daily_loss = self.starting_balance * self.max_daily_risk

        # Trigger if daily loss exceeds limit
        if today_pnl <= -max_daily_loss:
            self.trading_allowed = False
            print("\n" + "="*50)
            print("⚠ CIRCUIT BREAKER TRIGGERED ⚠")
            print(f"Daily loss: ${abs(today_pnl):.2f}")
            print(f"Limit: ${max_daily_loss:.2f}")
            print("Trading disabled for the day")
            print("="*50 + "\n")

        # Trigger if max consecutive losses reached
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.trading_allowed = False
            print("\n" + "="*50)
            print("⚠ CIRCUIT BREAKER TRIGGERED ⚠")
            print(f"Consecutive losses: {self.consecutive_losses}")
            print("Trading disabled")
            print("="*50 + "\n")

    def get_risk_summary(self) -> Dict:
        """Get current risk status summary"""
        today = date.today()

        current_exposure = sum(pos['risk_amount'] for pos in self.open_positions)
        max_exposure = self.account_balance * self.max_total_exposure
        exposure_percent = (current_exposure / max_exposure) * 100 if max_exposure > 0 else 0

        today_trades = self.daily_trades.get(today, 0)
        today_pnl = self.daily_pnl.get(today, 0)

        return {
            'account_balance': self.account_balance,
            'starting_balance': self.starting_balance,
            'total_pnl': self.account_balance - self.starting_balance,
            'total_pnl_percent': ((self.account_balance / self.starting_balance) - 1) * 100,
            'open_positions': len(self.open_positions),
            'current_exposure': current_exposure,
            'exposure_used_percent': exposure_percent,
            'daily_trades': today_trades,
            'daily_pnl': today_pnl,
            'consecutive_losses': self.consecutive_losses,
            'trading_allowed': self.trading_allowed
        }

    def print_risk_summary(self):
        """Print formatted risk summary"""
        summary = self.get_risk_summary()

        print("\n" + "="*60)
        print("RISK MANAGEMENT SUMMARY")
        print("="*60)
        print(f"Account Balance:        ${summary['account_balance']:,.2f}")
        print(f"Starting Balance:       ${summary['starting_balance']:,.2f}")
        print(f"Total P&L:              ${summary['total_pnl']:,.2f} ({summary['total_pnl_percent']:+.2f}%)")
        print(f"\nOpen Positions:         {summary['open_positions']}/{self.max_positions}")
        print(f"Current Exposure:       ${summary['current_exposure']:.2f}")
        print(f"Exposure Used:          {summary['exposure_used_percent']:.1f}%")
        print(f"\nToday's Trades:         {summary['daily_trades']}/{self.max_trades_per_day}")
        print(f"Today's P&L:            ${summary['daily_pnl']:,.2f}")
        print(f"Consecutive Losses:     {summary['consecutive_losses']}/{self.max_consecutive_losses}")
        print(f"\nTrading Status:         {'✓ ENABLED' if summary['trading_allowed'] else '✗ DISABLED'}")
        print("="*60 + "\n")

    def reset_daily_limits(self):
        """Reset daily limits (call at start of new trading day)"""
        today = date.today()
        yesterday = today - pd.Timedelta(days=1)

        # Clear old daily data
        if yesterday in self.daily_trades:
            del self.daily_trades[yesterday]
        if yesterday in self.daily_pnl:
            del self.daily_pnl[yesterday]

        # Reset circuit breaker if new day
        if self.consecutive_losses < self.max_consecutive_losses:
            self.trading_allowed = True

        print("✓ Daily limits reset for new trading day")


# Example usage
if __name__ == "__main__":
    print("=== Risk Manager Example ===\n")

    # Initialize risk manager with $10,000 account
    rm = RiskManager(
        account_balance=10000,
        max_risk_per_trade=0.02,  # 2%
        max_daily_risk=0.05,  # 5%
        max_total_exposure=0.06,  # 6%
        max_positions=3
    )

    # Example 1: Calculate position size
    print("Example 1: Calculate Position Size")
    print("-" * 40)

    entry_price = 1.4500
    stop_loss_price = 1.4475  # 25 pips stop loss

    trade_risk = rm.calculate_position_size(entry_price, stop_loss_price)

    print(f"Entry Price:     {entry_price:.5f}")
    print(f"Stop Loss:       {stop_loss_price:.5f}")
    print(f"Stop Loss Pips:  {trade_risk.stop_loss_pips:.1f}")
    print(f"Position Size:   {trade_risk.position_size} units ({trade_risk.position_size/100000:.2f} lots)")
    print(f"Risk Amount:     ${trade_risk.risk_amount:.2f}")
    print(f"Risk Percent:    {trade_risk.risk_percent*100:.2f}%")

    # Example 2: Check if can open position
    print("\n\nExample 2: Position Approval Check")
    print("-" * 40)

    can_open, reason = rm.can_open_position(trade_risk)
    print(f"Can open position: {can_open}")
    print(f"Reason: {reason}")

    if can_open:
        rm.register_trade(trade_risk, "TRADE_001")

    # Example 3: Volatility-adjusted sizing
    print("\n\nExample 3: Volatility-Adjusted Sizing")
    print("-" * 40)

    current_atr = 0.0080  # High volatility
    normal_atr = 0.0060   # Normal volatility

    adjusted_risk = rm.calculate_volatility_adjusted_size(
        entry_price, stop_loss_price, current_atr, normal_atr
    )

    print(f"Normal Position:  {trade_risk.position_size} units")
    print(f"Adjusted Position: {adjusted_risk.position_size} units")
    print(f"Adjustment:       {(adjusted_risk.position_size/trade_risk.position_size - 1)*100:+.1f}%")

    # Example 4: Close trade
    print("\n\nExample 4: Close Trade")
    print("-" * 40)

    # Simulate winning trade
    pnl = 150.0
    rm.close_trade("TRADE_001", pnl, is_winner=True)

    # Example 5: Risk summary
    print("\n\nExample 5: Risk Summary")
    rm.print_risk_summary()

    # Example 6: Simulate multiple trades to show limits
    print("\n\nExample 6: Testing Risk Limits")
    print("-" * 40)

    # Try to open 3 more positions
    for i in range(3):
        trade_risk_new = rm.calculate_position_size(1.4500, 1.4475)
        can_open, reason = rm.can_open_position(trade_risk_new)

        print(f"\nTrade {i+2}: {can_open} - {reason}")

        if can_open:
            rm.register_trade(trade_risk_new, f"TRADE_00{i+2}")

    # Show final summary
    print("\n\nFinal Risk Summary:")
    rm.print_risk_summary()
