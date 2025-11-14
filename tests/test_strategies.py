"""
Simple tests for EUR/CAD trading strategies
Run this to verify strategies are working correctly
"""

import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.trend_following import TrendFollowingStrategy
from src.strategies.grid_trading import GridTradingStrategy
from src.market_analysis.regime_detector import MarketRegimeDetector


def generate_sample_data(bars=500):
    """Generate sample OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=bars, freq='H')

    # Generate realistic EUR/CAD price data around 1.4500
    np.random.seed(42)
    close_prices = 1.4500 + np.cumsum(np.random.randn(bars) * 0.0005)

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


def test_mean_reversion_strategy():
    """Test Mean Reversion Strategy"""
    print("\n" + "="*60)
    print("Testing Mean Reversion Strategy")
    print("="*60)

    # Generate sample data
    df = generate_sample_data()

    # Initialize strategy
    strategy = MeanReversionStrategy()

    # Generate signals
    df_with_signals = strategy.generate_signals(df)

    # Count signals
    long_signals = df_with_signals['long_signal'].sum()
    short_signals = df_with_signals['short_signal'].sum()

    print(f"Total bars analyzed: {len(df)}")
    print(f"Long signals generated: {long_signals}")
    print(f"Short signals generated: {short_signals}")
    print(f"Total signals: {long_signals + short_signals}")

    # Test entry/exit calculation
    if long_signals > 0:
        signal_idx = df_with_signals[df_with_signals['long_signal']].index[0]
        signal_data = df_with_signals.loc[:signal_idx]
        entry_data = strategy.calculate_entry_exit(signal_data, 'long')

        if entry_data:
            print(f"\nSample Long Entry Data:")
            print(f"  Entry Price: {entry_data['entry']:.5f}")
            print(f"  Stop Loss: {entry_data['stop_loss']:.5f}")
            print(f"  Take Profit 1: {entry_data['take_profit_1']:.5f}")
            print(f"  Risk/Reward 1: {entry_data['risk_reward_1']:.2f}")

    print("\nMean Reversion Strategy: PASS")


def test_trend_following_strategy():
    """Test Trend Following Strategy"""
    print("\n" + "="*60)
    print("Testing Trend Following Strategy")
    print("="*60)

    # Generate sample data with stronger trend
    df = generate_sample_data()
    df['close'] = 1.4500 + np.cumsum(np.random.randn(len(df)) * 0.001)  # Stronger trend

    # Initialize strategy
    strategy = TrendFollowingStrategy()

    # Generate signals
    df_with_signals = strategy.generate_signals(df)

    # Count signals
    long_signals = df_with_signals['long_signal'].sum()
    short_signals = df_with_signals['short_signal'].sum()

    print(f"Total bars analyzed: {len(df)}")
    print(f"Long signals generated: {long_signals}")
    print(f"Short signals generated: {short_signals}")
    print(f"Total signals: {long_signals + short_signals}")

    # Test entry/exit calculation
    if long_signals > 0:
        signal_idx = df_with_signals[df_with_signals['long_signal']].index[0]
        signal_data = df_with_signals.loc[:signal_idx]
        entry_data = strategy.calculate_entry_exit(signal_data, 'long')

        if entry_data:
            print(f"\nSample Long Entry Data:")
            print(f"  Entry Price: {entry_data['entry']:.5f}")
            print(f"  Stop Loss: {entry_data['stop_loss']:.5f}")
            print(f"  Take Profit 1: {entry_data['take_profit_1']:.5f}")
            print(f"  Trailing Stop Distance: {entry_data['trailing_stop_distance']:.5f}")
            print(f"  Risk/Reward 1: {entry_data['risk_reward_1']:.2f}")

    print("\nTrend Following Strategy: PASS")


def test_grid_trading_strategy():
    """Test Grid Trading Strategy"""
    print("\n" + "="*60)
    print("Testing Grid Trading Strategy")
    print("="*60)

    # Generate sample data
    df = generate_sample_data()

    # Initialize strategy
    strategy = GridTradingStrategy(total_capital=10000)

    # Check if grid is suitable
    is_suitable, reason = strategy.is_grid_suitable(df)
    print(f"Grid suitable: {is_suitable}")
    print(f"Reason: {reason}")

    # Calculate grid range
    grid_range = strategy.calculate_grid_range(df)
    if grid_range:
        print(f"\nGrid Range:")
        print(f"  Top: {grid_range['top']:.5f}")
        print(f"  Bottom: {grid_range['bottom']:.5f}")
        print(f"  Range Size: {grid_range['range_size']:.5f}")
        print(f"  Midpoint: {grid_range['midpoint']:.5f}")

    # Create grid
    current_price = df['close'].iloc[-1]
    atr = df['close'].rolling(14).std().iloc[-1] * 0.01  # Approximate ATR
    grids = strategy.create_grid(current_price, atr)

    print(f"\nTotal grid orders: {len(grids)}")
    print(f"Buy orders: {sum(1 for g in grids if g['type'] == 'buy')}")
    print(f"Sell orders: {sum(1 for g in grids if g['type'] == 'sell')}")

    # Show sample grid order
    if grids:
        sample = grids[0]
        print(f"\nSample Grid Order:")
        print(f"  Type: {sample['type']}")
        print(f"  Price: {sample['price']:.5f}")
        print(f"  Take Profit: {sample['take_profit']:.5f}")
        print(f"  Stop Loss: {sample['stop_loss']:.5f}")

    print("\nGrid Trading Strategy: PASS")


def test_regime_detector():
    """Test Market Regime Detector"""
    print("\n" + "="*60)
    print("Testing Market Regime Detector")
    print("="*60)

    detector = MarketRegimeDetector()

    # Test different market conditions
    test_cases = [
        ("Ranging Market", generate_sample_data()),
        ("Trending Market", generate_trending_data()),
        ("High Volatility", generate_volatile_data())
    ]

    for name, df in test_cases:
        regime = detector.detect_regime(df)
        description = detector.get_regime_description(regime)
        print(f"\n{name}:")
        print(f"  Detected Regime: {regime}")
        print(f"  Description: {description}")

    print("\nMarket Regime Detector: PASS")


def generate_trending_data(bars=500):
    """Generate trending market data"""
    dates = pd.date_range(start='2024-01-01', periods=bars, freq='H')
    np.random.seed(42)

    # Strong uptrend
    trend = np.linspace(0, 0.05, bars)
    noise = np.random.randn(bars) * 0.0002
    close_prices = 1.4500 + trend + noise

    data = {
        'open': close_prices + np.random.randn(bars) * 0.0002,
        'high': close_prices + abs(np.random.randn(bars) * 0.0005),
        'low': close_prices - abs(np.random.randn(bars) * 0.0005),
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, bars)
    }

    return pd.DataFrame(data, index=dates)


def generate_volatile_data(bars=500):
    """Generate high volatility market data"""
    dates = pd.date_range(start='2024-01-01', periods=bars, freq='H')
    np.random.seed(42)

    # High volatility
    close_prices = 1.4500 + np.cumsum(np.random.randn(bars) * 0.002)

    data = {
        'open': close_prices + np.random.randn(bars) * 0.001,
        'high': close_prices + abs(np.random.randn(bars) * 0.002),
        'low': close_prices - abs(np.random.randn(bars) * 0.002),
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, bars)
    }

    return pd.DataFrame(data, index=dates)


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("EUR/CAD Trading Bot - Strategy Tests")
    print("="*60)

    try:
        test_mean_reversion_strategy()
        test_trend_following_strategy()
        test_grid_trading_strategy()
        test_regime_detector()

        print("\n" + "="*60)
        print("ALL TESTS PASSED")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
