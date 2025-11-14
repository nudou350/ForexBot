"""
Example: How to run backtests on EUR/CAD strategies
This demonstrates backtesting with historical data
"""

import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.backtesting.backtester import Backtester
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.trend_following import TrendFollowingStrategy


def generate_sample_historical_data(bars=2000):
    """
    Generate sample EUR/CAD historical data
    In production, you would load actual historical data from IBKR or CSV
    """
    dates = pd.date_range(start='2023-01-01', periods=bars, freq='H')

    # Generate realistic EUR/CAD price movements
    np.random.seed(42)

    # Base price around 1.45
    base_price = 1.4500

    # Create trending periods and ranging periods
    trend_periods = bars // 4
    trends = []

    for _ in range(4):
        # Alternate between trending and ranging
        if np.random.rand() > 0.5:
            # Trending period
            trend = np.cumsum(np.random.randn(trend_periods) * 0.0008)
        else:
            # Ranging period
            trend = np.random.randn(trend_periods) * 0.0003

        trends.extend(trend)

    trends = np.array(trends[:bars])
    close_prices = base_price + trends

    # Generate OHLCV
    data = {
        'open': close_prices + np.random.randn(bars) * 0.0002,
        'high': close_prices + abs(np.random.randn(bars) * 0.0005),
        'low': close_prices - abs(np.random.randn(bars) * 0.0005),
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, bars)
    }

    df = pd.DataFrame(data, index=dates)
    return df


def run_mean_reversion_backtest():
    """Backtest Mean Reversion Strategy"""
    print("\n" + "="*70)
    print("BACKTESTING MEAN REVERSION STRATEGY")
    print("="*70)

    # Generate or load historical data
    df = generate_sample_historical_data(2000)
    print(f"\nData period: {df.index[0]} to {df.index[-1]}")
    print(f"Total bars: {len(df)}")

    # Initialize backtester and strategy
    backtester = Backtester(initial_capital=10000, commission_pips=0.6)
    strategy = MeanReversionStrategy()

    # Split data into train and test
    split_point = int(len(df) * 0.7)
    train_data = df.iloc[:split_point]
    test_data = df.iloc[split_point:]

    # Run backtest on test data
    print(f"\nBacktesting on test period: {test_data.index[0]} to {test_data.index[-1]}")

    results = backtester.run_backtest(
        df,
        strategy,
        str(test_data.index[0]),
        str(test_data.index[-1])
    )

    # Print results
    print_backtest_results(results)

    return results


def run_trend_following_backtest():
    """Backtest Trend Following Strategy"""
    print("\n" + "="*70)
    print("BACKTESTING TREND FOLLOWING STRATEGY")
    print("="*70)

    # Generate or load historical data
    df = generate_sample_historical_data(2000)
    print(f"\nData period: {df.index[0]} to {df.index[-1]}")
    print(f"Total bars: {len(df)}")

    # Initialize backtester and strategy
    backtester = Backtester(initial_capital=10000, commission_pips=0.6)
    strategy = TrendFollowingStrategy()

    # Split data into train and test
    split_point = int(len(df) * 0.7)
    train_data = df.iloc[:split_point]
    test_data = df.iloc[split_point:]

    # Run backtest on test data
    print(f"\nBacktesting on test period: {test_data.index[0]} to {test_data.index[-1]}")

    results = backtester.run_backtest(
        df,
        strategy,
        str(test_data.index[0]),
        str(test_data.index[-1])
    )

    # Print results
    print_backtest_results(results)

    return results


def run_walk_forward_analysis():
    """Run walk-forward analysis"""
    print("\n" + "="*70)
    print("WALK-FORWARD ANALYSIS")
    print("="*70)

    # Generate longer historical data
    df = generate_sample_historical_data(5000)
    print(f"\nData period: {df.index[0]} to {df.index[-1]}")
    print(f"Total bars: {len(df)}")

    # Initialize backtester and strategy
    backtester = Backtester(initial_capital=10000)
    strategy = MeanReversionStrategy()

    # Run walk-forward analysis
    print("\nRunning walk-forward analysis...")
    print("Train period: 6 months, Test period: 1 month")

    results, all_metrics = backtester.walk_forward_analysis(
        df,
        strategy,
        train_period_months=6,
        test_period_months=1
    )

    if len(all_metrics) > 0:
        print("\n" + "="*70)
        print("WALK-FORWARD RESULTS SUMMARY")
        print("="*70)
        print(f"\nNumber of test periods: {len(results)}")
        print(f"\nAggregated Metrics:")
        print(f"  Average Win Rate: {all_metrics['win_rate'].mean():.2%}")
        print(f"  Win Rate Std Dev: {all_metrics['win_rate'].std():.2%}")
        print(f"  Average Profit Factor: {all_metrics['profit_factor'].mean():.2f}")
        print(f"  Average Sharpe Ratio: {all_metrics['sharpe_ratio'].mean():.2f}")
        print(f"  Average Max Drawdown: {all_metrics['max_drawdown'].mean():.2%}")
        print(f"  Average Total Return: {all_metrics['total_return'].mean():.2%}")

        # Show period-by-period results
        print("\nPeriod-by-Period Results:")
        print("-" * 70)
        for i, result in enumerate(results):
            metrics = result['metrics']
            print(f"\nPeriod {i+1}:")
            print(f"  Test Period: {result['test_start']} to {result['test_end']}")
            print(f"  Win Rate: {metrics['win_rate']:.2%}")
            print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
            print(f"  Total Return: {metrics['total_return']:.2%}")

    return results, all_metrics


def print_backtest_results(results):
    """Print formatted backtest results"""
    if not results or 'metrics' not in results:
        print("\nNo results to display")
        return

    metrics = results['metrics']

    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)

    print(f"\nPerformance Metrics:")
    print(f"  Total Trades: {metrics['total_trades']}")
    print(f"  Win Rate: {metrics['win_rate']:.2%}")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Average R:R: {metrics['avg_rr']:.2f}")

    print(f"\nReturn Metrics:")
    print(f"  Total Return: {metrics['total_return']:.2%}")
    print(f"  Final Equity: ${metrics['final_equity']:,.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")

    print(f"\nTrade Analysis:")
    print(f"  Average Win: ${metrics['avg_win']:.2f}")
    print(f"  Average Loss: ${metrics['avg_loss']:.2f}")

    # Detailed trade list
    if 'trades' in results and len(results['trades']) > 0:
        trades = results['trades']
        print(f"\nTrade Details (showing first 5):")
        print("-" * 70)
        for i, trade in trades.head(5).iterrows():
            print(f"\nTrade:")
            print(f"  Entry: {trade['entry_time']} at {trade['entry_price']:.5f}")
            print(f"  Exit: {trade['exit_time']} at {trade['exit_price']:.5f}")
            print(f"  Type: {trade['type']}")
            print(f"  P&L: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
            print(f"  Reason: {trade['exit_reason']}")

    # Assessment
    print("\n" + "="*70)
    print("ASSESSMENT")
    print("="*70)

    if metrics['win_rate'] >= 0.60:
        print("Win Rate: EXCELLENT (>=60%)")
    elif metrics['win_rate'] >= 0.55:
        print("Win Rate: GOOD (>=55%)")
    else:
        print("Win Rate: NEEDS IMPROVEMENT (<55%)")

    if metrics['profit_factor'] >= 1.5:
        print("Profit Factor: EXCELLENT (>=1.5)")
    elif metrics['profit_factor'] >= 1.2:
        print("Profit Factor: GOOD (>=1.2)")
    else:
        print("Profit Factor: NEEDS IMPROVEMENT (<1.2)")

    if metrics['max_drawdown'] <= 0.15:
        print("Max Drawdown: ACCEPTABLE (<=15%)")
    else:
        print("Max Drawdown: TOO HIGH (>15%)")

    if metrics['sharpe_ratio'] >= 1.5:
        print("Sharpe Ratio: EXCELLENT (>=1.5)")
    elif metrics['sharpe_ratio'] >= 1.0:
        print("Sharpe Ratio: GOOD (>=1.0)")
    else:
        print("Sharpe Ratio: NEEDS IMPROVEMENT (<1.0)")


def main():
    """Run backtest examples"""
    print("\n" + "="*70)
    print("EUR/CAD TRADING BOT - BACKTEST EXAMPLES")
    print("="*70)

    # Run individual strategy backtests
    mr_results = run_mean_reversion_backtest()
    tf_results = run_trend_following_backtest()

    # Compare strategies
    print("\n" + "="*70)
    print("STRATEGY COMPARISON")
    print("="*70)

    if mr_results and tf_results:
        mr_metrics = mr_results['metrics']
        tf_metrics = tf_results['metrics']

        print(f"\nMean Reversion vs Trend Following:")
        print(f"  Win Rate: {mr_metrics['win_rate']:.2%} vs {tf_metrics['win_rate']:.2%}")
        print(f"  Profit Factor: {mr_metrics['profit_factor']:.2f} vs {tf_metrics['profit_factor']:.2f}")
        print(f"  Total Return: {mr_metrics['total_return']:.2%} vs {tf_metrics['total_return']:.2%}")
        print(f"  Max Drawdown: {mr_metrics['max_drawdown']:.2%} vs {tf_metrics['max_drawdown']:.2%}")

        if mr_metrics['total_return'] > tf_metrics['total_return']:
            print("\nBest Strategy: Mean Reversion")
        else:
            print("\nBest Strategy: Trend Following")

    # Run walk-forward analysis
    wf_results, wf_metrics = run_walk_forward_analysis()

    print("\n" + "="*70)
    print("BACKTESTING COMPLETE")
    print("="*70)
    print("\nNext Steps:")
    print("1. Review backtest results")
    print("2. Optimize strategy parameters if needed")
    print("3. Run paper trading for 3 months minimum")
    print("4. Only then proceed to live trading with small capital")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
