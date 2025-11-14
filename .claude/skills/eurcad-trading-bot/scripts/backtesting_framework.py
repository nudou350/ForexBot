"""
Backtesting Framework for EUR/CAD Trading Strategies
Validates strategies before live deployment
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
from dataclasses import dataclass


@dataclass
class BacktestResult:
    """Results from strategy backtest"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percent: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_percent: float
    avg_trade_duration: float
    trades: List[Dict]
    equity_curve: pd.Series


class Backtester:
    """
    Backtesting engine for trading strategies
    """

    def __init__(
        self,
        data: pd.DataFrame,
        initial_balance: float = 10000,
        risk_per_trade: float = 0.02,
        commission_per_lot: float = 2.0
    ):
        """
        Initialize backtester

        Args:
            data: DataFrame with OHLCV data
            initial_balance: Starting account balance
            risk_per_trade: Risk per trade (decimal)
            commission_per_lot: Commission cost per lot
        """
        self.data = data.copy()
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.commission_per_lot = commission_per_lot

        # Trading state
        self.balance = initial_balance
        self.equity = initial_balance
        self.trades = []
        self.equity_curve = []

        # Constants
        self.pip_value = 10  # $10 per pip per standard lot
        self.pip_size = 0.0001

    def run(
        self,
        strategy,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> BacktestResult:
        """
        Run backtest for a strategy

        Args:
            strategy: Strategy object with calculate_signals method
            start_date: Start date for backtest (optional)
            end_date: End date for backtest (optional)

        Returns:
            BacktestResult object
        """
        print(f"\n{'='*60}")
        print(f"Running Backtest: {strategy.name}")
        print(f"{'='*60}")

        # Filter data by date range
        data = self.data.copy()
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]

        print(f"Period: {data.index[0]} to {data.index[-1]}")
        print(f"Total bars: {len(data)}")

        # Reset state
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.trades = []
        self.equity_curve = [self.initial_balance]

        # Calculate signals
        data = strategy.calculate_signals(data)

        # Track open position
        position = None

        # Iterate through data
        for i in range(len(data)):
            current = data.iloc[i]

            # Skip if not enough data for indicators
            if pd.isna(current.get('signal', np.nan)):
                self.equity_curve.append(self.equity)
                continue

            # Check if we have an open position
            if position is not None:
                # Check for exit conditions
                exit_signal = self._check_exit(position, current, data.iloc[:i+1], strategy)

                if exit_signal:
                    # Close position
                    self._close_position(position, current, exit_signal)
                    position = None

            # Check for new entry signals
            elif current['signal'] != 0:
                # Open new position
                position = self._open_position(current, strategy, data.iloc[:i+1])

            # Update equity curve
            if position:
                # Mark-to-market
                self.equity = self.balance + self._calculate_unrealized_pnl(position, current)
            else:
                self.equity = self.balance

            self.equity_curve.append(self.equity)

        # Close any remaining open position
        if position is not None:
            last_bar = data.iloc[-1]
            self._close_position(position, last_bar, 'end_of_data')

        # Calculate results
        results = self._calculate_results()

        self._print_results(results)

        return results

    def _open_position(
        self,
        bar: pd.Series,
        strategy,
        historical_data: pd.DataFrame
    ) -> Dict:
        """Open new position"""
        action = 'BUY' if bar['signal'] == 1 else 'SELL'
        entry_price = bar['close']

        # Get stop loss and take profit from strategy
        stop_loss = strategy.get_stop_loss(historical_data, entry_price, action)
        take_profit = strategy.get_take_profit(historical_data, entry_price, action)

        # Calculate position size
        stop_pips = abs(entry_price - stop_loss) / self.pip_size
        risk_amount = self.balance * self.risk_per_trade
        position_size = self._calculate_position_size(risk_amount, stop_pips)

        # Calculate commission
        lots = position_size / 100000
        commission = lots * self.commission_per_lot

        position = {
            'entry_time': bar.name,
            'entry_price': entry_price,
            'action': action,
            'position_size': position_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_amount': risk_amount,
            'commission': commission
        }

        return position

    def _close_position(
        self,
        position: Dict,
        bar: pd.Series,
        exit_reason: str
    ):
        """Close position and record trade"""
        exit_price = bar['close']
        exit_time = bar.name

        # Calculate P&L
        if position['action'] == 'BUY':
            pnl_pips = (exit_price - position['entry_price']) / self.pip_size
        else:  # SELL
            pnl_pips = (position['entry_price'] - exit_price) / self.pip_size

        lots = position['position_size'] / 100000
        gross_pnl = pnl_pips * self.pip_value * lots
        net_pnl = gross_pnl - position['commission']

        # Update balance
        self.balance += net_pnl

        # Record trade
        trade = {
            'entry_time': position['entry_time'],
            'exit_time': exit_time,
            'duration': (exit_time - position['entry_time']).total_seconds() / 3600,  # hours
            'action': position['action'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'position_size': position['position_size'],
            'stop_loss': position['stop_loss'],
            'take_profit': position['take_profit'],
            'pnl_pips': pnl_pips,
            'gross_pnl': gross_pnl,
            'commission': position['commission'],
            'net_pnl': net_pnl,
            'exit_reason': exit_reason,
            'balance_after': self.balance
        }

        self.trades.append(trade)

    def _check_exit(
        self,
        position: Dict,
        bar: pd.Series,
        historical_data: pd.DataFrame,
        strategy
    ) -> Optional[str]:
        """Check if position should be exited"""
        # Check stop loss
        if position['action'] == 'BUY':
            if bar['low'] <= position['stop_loss']:
                return 'stop_loss'
        else:  # SELL
            if bar['high'] >= position['stop_loss']:
                return 'stop_loss'

        # Check take profit
        if position['take_profit']:
            if position['action'] == 'BUY':
                if bar['high'] >= position['take_profit']:
                    return 'take_profit'
            else:  # SELL
                if bar['low'] <= position['take_profit']:
                    return 'take_profit'

        # Check strategy exit signals
        if position['action'] == 'BUY' and bar.get('exit_long', False):
            return 'strategy_signal'
        elif position['action'] == 'SELL' and bar.get('exit_short', False):
            return 'strategy_signal'

        # Check opposite signal
        if position['action'] == 'BUY' and bar.get('signal', 0) == -1:
            return 'opposite_signal'
        elif position['action'] == 'SELL' and bar.get('signal', 0) == 1:
            return 'opposite_signal'

        return None

    def _calculate_unrealized_pnl(self, position: Dict, bar: pd.Series) -> float:
        """Calculate unrealized P&L for open position"""
        current_price = bar['close']

        if position['action'] == 'BUY':
            pnl_pips = (current_price - position['entry_price']) / self.pip_size
        else:
            pnl_pips = (position['entry_price'] - current_price) / self.pip_size

        lots = position['position_size'] / 100000
        return pnl_pips * self.pip_value * lots

    def _calculate_position_size(self, risk_amount: float, stop_pips: float) -> int:
        """Calculate position size in units"""
        risk_per_lot = self.pip_value * stop_pips
        lots = risk_amount / risk_per_lot
        position_size = int(lots * 100000)

        # Round to nearest 1000 units
        position_size = round(position_size / 1000) * 1000

        # Minimum 1000 units
        return max(position_size, 1000)

    def _calculate_results(self) -> BacktestResult:
        """Calculate backtest statistics"""
        if not self.trades:
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_pnl_percent=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                max_drawdown_percent=0.0,
                avg_trade_duration=0.0,
                trades=[],
                equity_curve=pd.Series(self.equity_curve)
            )

        trades_df = pd.DataFrame(self.trades)

        # Basic stats
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['net_pnl'] > 0])
        losing_trades = len(trades_df[trades_df['net_pnl'] <= 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        # P&L stats
        total_pnl = trades_df['net_pnl'].sum()
        total_pnl_percent = (total_pnl / self.initial_balance) * 100

        winners = trades_df[trades_df['net_pnl'] > 0]['net_pnl']
        losers = trades_df[trades_df['net_pnl'] <= 0]['net_pnl']

        avg_win = winners.mean() if len(winners) > 0 else 0
        avg_loss = losers.mean() if len(losers) > 0 else 0
        largest_win = winners.max() if len(winners) > 0 else 0
        largest_loss = losers.min() if len(losers) > 0 else 0

        # Profit factor
        total_wins = winners.sum() if len(winners) > 0 else 0
        total_losses = abs(losers.sum()) if len(losers) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Sharpe ratio (simplified)
        returns = trades_df['net_pnl'] / self.initial_balance
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

        # Drawdown
        equity_series = pd.Series(self.equity_curve)
        running_max = equity_series.expanding().max()
        drawdown = equity_series - running_max
        max_drawdown = drawdown.min()
        max_drawdown_percent = (max_drawdown / running_max[drawdown.idxmin()]) * 100

        # Average trade duration
        avg_duration = trades_df['duration'].mean()

        return BacktestResult(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            avg_trade_duration=avg_duration,
            trades=self.trades,
            equity_curve=equity_series
        )

    def _print_results(self, results: BacktestResult):
        """Print formatted backtest results"""
        print(f"\n{'='*60}")
        print("BACKTEST RESULTS")
        print(f"{'='*60}")
        print(f"\nPerformance Metrics:")
        print(f"  Total Trades:          {results.total_trades}")
        print(f"  Winning Trades:        {results.winning_trades}")
        print(f"  Losing Trades:         {results.losing_trades}")
        print(f"  Win Rate:              {results.win_rate:.2f}%")
        print(f"\nP&L Metrics:")
        print(f"  Total P&L:             ${results.total_pnl:,.2f} ({results.total_pnl_percent:+.2f}%)")
        print(f"  Average Win:           ${results.avg_win:.2f}")
        print(f"  Average Loss:          ${results.avg_loss:.2f}")
        print(f"  Largest Win:           ${results.largest_win:.2f}")
        print(f"  Largest Loss:          ${results.largest_loss:.2f}")
        print(f"  Profit Factor:         {results.profit_factor:.2f}")
        print(f"\nRisk Metrics:")
        print(f"  Sharpe Ratio:          {results.sharpe_ratio:.2f}")
        print(f"  Max Drawdown:          ${results.max_drawdown:,.2f} ({results.max_drawdown_percent:.2f}%)")
        print(f"\nOther:")
        print(f"  Avg Trade Duration:    {results.avg_trade_duration:.1f} hours")
        print(f"\nFinal Balance:           ${self.balance:,.2f}")
        print(f"{'='*60}\n")

        # Assessment
        self._print_assessment(results)

    def _print_assessment(self, results: BacktestResult):
        """Print strategy assessment"""
        print("STRATEGY ASSESSMENT")
        print("-" * 60)

        passed = []
        failed = []

        # Check win rate
        if results.win_rate >= 60:
            passed.append(f"✓ Win rate: {results.win_rate:.1f}% (target: ≥60%)")
        else:
            failed.append(f"✗ Win rate: {results.win_rate:.1f}% (target: ≥60%)")

        # Check profit factor
        if results.profit_factor >= 1.5:
            passed.append(f"✓ Profit factor: {results.profit_factor:.2f} (target: ≥1.5)")
        else:
            failed.append(f"✗ Profit factor: {results.profit_factor:.2f} (target: ≥1.5)")

        # Check max drawdown
        if abs(results.max_drawdown_percent) <= 15:
            passed.append(f"✓ Max drawdown: {abs(results.max_drawdown_percent):.1f}% (target: ≤15%)")
        else:
            failed.append(f"✗ Max drawdown: {abs(results.max_drawdown_percent):.1f}% (target: ≤15%)")

        # Check Sharpe ratio
        if results.sharpe_ratio >= 1.0:
            passed.append(f"✓ Sharpe ratio: {results.sharpe_ratio:.2f} (target: ≥1.0)")
        else:
            failed.append(f"✗ Sharpe ratio: {results.sharpe_ratio:.2f} (target: ≥1.0)")

        # Check positive P&L
        if results.total_pnl > 0:
            passed.append(f"✓ Positive P&L: ${results.total_pnl:,.2f}")
        else:
            failed.append(f"✗ Negative P&L: ${results.total_pnl:,.2f}")

        # Print results
        if passed:
            print("\nPassed Criteria:")
            for item in passed:
                print(f"  {item}")

        if failed:
            print("\nFailed Criteria:")
            for item in failed:
                print(f"  {item}")

        # Overall assessment
        print("\n" + "-" * 60)
        if len(failed) == 0:
            print("✓ STRATEGY APPROVED FOR PAPER TRADING")
        elif len(failed) <= 2:
            print("⚠ STRATEGY NEEDS OPTIMIZATION")
        else:
            print("✗ STRATEGY NOT READY - REQUIRES MAJOR IMPROVEMENTS")
        print("-" * 60 + "\n")

    def plot_results(self, results: BacktestResult):
        """Plot equity curve and drawdown"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        # Equity curve
        results.equity_curve.plot(ax=ax1, color='blue', linewidth=2)
        ax1.axhline(y=self.initial_balance, color='gray', linestyle='--', label='Starting Balance')
        ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Trade Number')
        ax1.set_ylabel('Account Balance ($)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Drawdown
        running_max = results.equity_curve.expanding().max()
        drawdown = ((results.equity_curve - running_max) / running_max) * 100
        drawdown.plot(ax=ax2, color='red', linewidth=2, label='Drawdown')
        ax2.fill_between(drawdown.index, 0, drawdown, color='red', alpha=0.3)
        ax2.set_title('Drawdown', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Trade Number')
        ax2.set_ylabel('Drawdown (%)')
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        plt.tight_layout()
        plt.savefig('backtest_results.png', dpi=300, bbox_inches='tight')
        print("✓ Chart saved as 'backtest_results.png'")


# Example usage
if __name__ == "__main__":
    # Generate sample data
    print("Generating sample EUR/CAD data...")
    dates = pd.date_range('2022-01-01', '2024-12-31', freq='H')
    n = len(dates)

    # Simulated EUR/CAD price movement
    np.random.seed(42)
    price = 1.4500
    prices = [price]

    for _ in range(n-1):
        change = np.random.randn() * 0.0005
        price = price * (1 + change)
        prices.append(price)

    data = pd.DataFrame({
        'open': prices,
        'high': [p * 1.0002 for p in prices],
        'low': [p * 0.9998 for p in prices],
        'close': prices,
    }, index=dates)

    print(f"✓ Generated {len(data)} bars of data")

    # Import strategy (would normally come from strategy_template.py)
    from strategy_template import get_strategy

    # Test Mean Reversion Strategy
    strategy = get_strategy('mean_reversion')

    # Run backtest
    backtester = Backtester(
        data=data,
        initial_balance=10000,
        risk_per_trade=0.02
    )

    results = backtester.run(strategy)

    # Plot results
    # backtester.plot_results(results)  # Uncomment to generate plot

    print("\nBacktest complete!")
