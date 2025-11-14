"""
Backtesting Framework for EUR/CAD Trading Bot
Walk-forward analysis with out-of-sample testing
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config


class Backtester:
    """
    Backtest trading strategies on historical EUR/CAD data
    Walk-forward analysis with comprehensive metrics
    """

    def __init__(self, initial_capital: float = None, commission_pips: float = None):
        """
        Initialize backtester

        Args:
            initial_capital: Starting capital
            commission_pips: Commission in pips per trade
        """
        self.initial_capital = initial_capital or config.INITIAL_CAPITAL
        self.commission_pips = commission_pips or config.BACKTEST_COMMISSION_PIPS
        self.pip_value = config.EURCAD_PIP_VALUE
        self.logger = logging.getLogger(__name__)

    def run_backtest(self, df: pd.DataFrame, strategy,
                    start_date: str, end_date: str) -> Dict:
        """
        Run backtest on historical data

        Args:
            df: DataFrame with OHLCV data
            strategy: Strategy instance
            start_date: Start date for backtest
            end_date: End date for backtest

        Returns:
            Dictionary with backtest results
        """
        # Filter data
        df_test = df[(df.index >= start_date) & (df.index <= end_date)].copy()

        if len(df_test) < 100:
            self.logger.warning("Insufficient data for backtest")
            return {}

        # Initialize tracking
        capital = self.initial_capital
        positions = []
        trades = []
        equity_curve = [capital]

        # Generate signals
        df_test = strategy.generate_signals(df_test)

        # Simulate trading
        for i in range(100, len(df_test)):  # Skip first 100 bars for indicators
            current_bar = df_test.iloc[i]

            # Check for entry signals
            if current_bar.get('long_signal', False) and len(positions) == 0:
                entry_data = strategy.calculate_entry_exit(
                    df_test.iloc[:i+1], 'long'
                )

                if entry_data:
                    position = self._open_position(
                        'long', current_bar, entry_data, capital, i
                    )
                    positions.append(position)

            elif current_bar.get('short_signal', False) and len(positions) == 0:
                entry_data = strategy.calculate_entry_exit(
                    df_test.iloc[:i+1], 'short'
                )

                if entry_data:
                    position = self._open_position(
                        'short', current_bar, entry_data, capital, i
                    )
                    positions.append(position)

            # Check for exit conditions
            closed_positions = []
            for pos in positions:
                close_result = self._check_exit(pos, current_bar, i)

                if close_result:
                    pnl = self._calculate_pnl(pos, close_result)
                    capital += pnl

                    trades.append({
                        'entry_time': pos['entry_time'],
                        'exit_time': close_result['time'],
                        'type': pos['type'],
                        'entry_price': pos['entry_price'],
                        'exit_price': close_result['price'],
                        'pnl': pnl,
                        'pnl_pct': (pnl / capital) * 100,
                        'exit_reason': close_result['reason']
                    })

                    closed_positions.append(pos)

            # Remove closed positions
            positions = [p for p in positions if p not in closed_positions]

            # Update equity curve
            unrealized_pnl = sum([
                self._calculate_unrealized_pnl(p, current_bar)
                for p in positions
            ])
            equity_curve.append(capital + unrealized_pnl)

        # Calculate metrics
        metrics = self._calculate_metrics(trades, equity_curve)

        return {
            'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
            'metrics': metrics,
            'equity_curve': equity_curve,
            'final_capital': capital
        }

    def _open_position(self, position_type: str, bar: pd.Series,
                      entry_data: Dict, capital: float, index: int) -> Dict:
        """Open a new position"""
        # Calculate position size (1% risk)
        risk_per_trade = capital * 0.01
        stop_distance = abs(entry_data['entry'] - entry_data['stop_loss'])

        if stop_distance == 0:
            position_size = 0
        else:
            position_size = (risk_per_trade / stop_distance) * entry_data['entry']

        return {
            'type': position_type,
            'entry_price': entry_data['entry'],
            'entry_time': bar.name,
            'entry_index': index,
            'stop_loss': entry_data['stop_loss'],
            'take_profit_1': entry_data['take_profit_1'],
            'take_profit_2': entry_data.get('take_profit_2'),
            'size': position_size,
            'partial_closed': False
        }

    def _check_exit(self, position: Dict, bar: pd.Series,
                   index: int) -> Optional[Dict]:
        """Check if position should be closed"""
        # Check stop loss
        if position['type'] == 'long':
            if bar['low'] <= position['stop_loss']:
                return {
                    'price': position['stop_loss'],
                    'time': bar.name,
                    'reason': 'stop_loss'
                }

            # Check take profit
            if bar['high'] >= position['take_profit_1']:
                return {
                    'price': position['take_profit_1'],
                    'time': bar.name,
                    'reason': 'take_profit'
                }

        else:  # short
            if bar['high'] >= position['stop_loss']:
                return {
                    'price': position['stop_loss'],
                    'time': bar.name,
                    'reason': 'stop_loss'
                }

            if bar['low'] <= position['take_profit_1']:
                return {
                    'price': position['take_profit_1'],
                    'time': bar.name,
                    'reason': 'take_profit'
                }

        # Time-based exit (optional - for mean reversion)
        if index - position['entry_index'] > 48:  # 48 hours for 1H timeframe
            return {
                'price': bar['close'],
                'time': bar.name,
                'reason': 'time_exit'
            }

        return None

    def _calculate_pnl(self, position: Dict, close_result: Dict) -> float:
        """Calculate P&L for closed position"""
        if position['type'] == 'long':
            price_change = close_result['price'] - position['entry_price']
        else:
            price_change = position['entry_price'] - close_result['price']

        # Subtract commission
        pnl = ((price_change - (self.commission_pips * self.pip_value)) *
               position['size'])

        return pnl

    def _calculate_unrealized_pnl(self, position: Dict, bar: pd.Series) -> float:
        """Calculate unrealized P&L"""
        if position['type'] == 'long':
            return (bar['close'] - position['entry_price']) * position['size']
        else:
            return (position['entry_price'] - bar['close']) * position['size']

    def _calculate_metrics(self, trades_list: List[Dict],
                          equity_curve: List[float]) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not trades_list:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'avg_rr': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'total_return': 0,
                'final_equity': equity_curve[-1] if equity_curve else 0
            }

        trades = pd.DataFrame(trades_list)

        # Win rate
        winning_trades = trades[trades['pnl'] > 0]
        losing_trades = trades[trades['pnl'] < 0]
        win_rate = len(winning_trades) / len(trades) if len(trades) > 0 else 0

        # Profit factor
        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = (gross_profit / gross_loss if gross_loss > 0
                        else float('inf') if gross_profit > 0 else 0)

        # Average win/loss
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0

        # Max drawdown
        equity = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        max_drawdown = abs(np.min(drawdown))

        # Sharpe ratio
        returns = trades['pnl_pct'].values
        sharpe_ratio = (np.mean(returns) / np.std(returns) * np.sqrt(252)
                       if len(returns) > 0 and np.std(returns) > 0 else 0)

        # Total return
        total_return = ((equity[-1] - equity[0]) / equity[0]
                       if len(equity) > 0 and equity[0] > 0 else 0)

        return {
            'total_trades': len(trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_rr': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_return': total_return,
            'final_equity': equity[-1] if len(equity) > 0 else 0
        }

    def walk_forward_analysis(self, df: pd.DataFrame, strategy,
                             train_period_months: int = None,
                             test_period_months: int = None) -> Tuple[List, pd.DataFrame]:
        """
        Walk-forward analysis: train on historical data, test on forward period

        Args:
            df: DataFrame with OHLCV data
            strategy: Strategy instance
            train_period_months: Training period in months
            test_period_months: Testing period in months

        Returns:
            Tuple of (results list, metrics DataFrame)
        """
        train_period = (train_period_months or
                       config.BACKTEST_TRAIN_PERIOD_MONTHS)
        test_period = (test_period_months or
                      config.BACKTEST_TEST_PERIOD_MONTHS)

        results = []

        start_date = df.index[0]
        end_date = df.index[-1]

        current_date = start_date

        while current_date < end_date:
            # Define training period
            train_start = current_date
            train_end = train_start + timedelta(days=train_period * 30)

            # Define testing period
            test_start = train_end
            test_end = test_start + timedelta(days=test_period * 30)

            if test_end > end_date:
                break

            # Run backtest on test period
            result = self.run_backtest(df, strategy, str(test_start), str(test_end))

            if result:
                results.append({
                    'test_start': test_start,
                    'test_end': test_end,
                    'metrics': result['metrics'],
                    'trades': result.get('trades')
                })

            # Move forward
            current_date = test_end

        # Aggregate results
        if results:
            all_metrics = pd.DataFrame([r['metrics'] for r in results])

            print("\n=== Walk-Forward Analysis Results ===")
            print(f"Number of periods: {len(results)}")
            print(f"Average win rate: {all_metrics['win_rate'].mean():.2%}")
            print(f"Average profit factor: {all_metrics['profit_factor'].mean():.2f}")
            print(f"Average Sharpe ratio: {all_metrics['sharpe_ratio'].mean():.2f}")
            print(f"Average max drawdown: {all_metrics['max_drawdown'].mean():.2%}")

            return results, all_metrics
        else:
            return [], pd.DataFrame()
