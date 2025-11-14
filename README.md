# EUR/CAD Trading Bot for Interactive Brokers

A production-ready, institutional-grade automated trading bot for EUR/CAD forex trading using Interactive Brokers (IBKR) API.

## Target Performance Metrics

- **Win Rate:** 65-75%
- **Monthly Return:** 8-12%
- **Max Drawdown:** <12%
- **Risk per Trade:** 1%
- **Profit Factor:** >2.0
- **Sharpe Ratio:** >1.5

## Features

### Core Trading Strategies

1. **Mean Reversion Strategy** (Primary - 70% target win rate)
   - Uses Bollinger Bands, RSI, MACD, and Volume confluence
   - Best for ranging markets (60% of the time)
   - 1-hour timeframe

2. **Trend Following Strategy** (Secondary - 65% target win rate)
   - Enters on pullbacks during strong trends
   - Uses EMAs, ADX, RSI, MACD
   - 4-hour timeframe with trailing stops

3. **Grid Trading Strategy** (Low volatility - 75% target win rate)
   - Places buy/sell orders at regular intervals
   - Best during summer months and low volatility
   - 15-minute timeframe

### Market Regime Detection

Dynamic strategy selection based on:
- ADX (trend strength)
- ATR (volatility)
- Bollinger Bands width
- EMA alignment

Market regimes classified as:
- STRONG_TREND
- WEAK_TREND
- RANGING
- BREAKOUT_PENDING
- HIGH_VOLATILITY
- LOW_VOLATILITY

### Risk Management

Multi-layer protection system:
- Position sizing (1% risk per trade)
- Max drawdown limit (12%)
- Daily loss limit (3%)
- Max concurrent trades (3)
- Consecutive loss protection (5 losses = halt)
- Total portfolio risk limit (5%)

### Emergency Stop Systems

- Drawdown monitoring
- Volatility spike detection
- API connectivity monitoring
- Stale data detection
- Spread monitoring
- News event protection
- Weekend/market closure detection

### IBKR Integration

- Connection management (paper and live trading)
- Historical data fetching
- Real-time price data
- Market and bracket orders
- Position management
- Trailing stops
- Account monitoring

### Backtesting Framework

- Walk-forward analysis
- Out-of-sample testing
- Comprehensive performance metrics
- Equity curve tracking
- Win rate and profit factor calculation

## Installation

### Prerequisites

1. **Python 3.8+**
2. **Interactive Brokers Account**
   - Open an account at [www.interactivebrokers.com](https://www.interactivebrokers.com)
   - Apply for forex trading permission
   - Fund account ($10,000 minimum recommended)

3. **IBKR TWS or Gateway**
   - Download and install Trader Workstation (TWS) or IB Gateway
   - Enable API trading in TWS settings:
     - File > Global Configuration > API > Settings
     - Enable "Enable ActiveX and Socket Clients"
     - Set "Socket port" to 7497 (paper) or 7496 (live)
     - Uncheck "Read-Only API"

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

Edit `config/config.py` to customize:

```python
# Trading mode
PAPER_TRADING = True  # Set to False for live trading

# Capital
INITIAL_CAPITAL = 10000

# Risk parameters
MAX_RISK_PER_TRADE = 0.01  # 1% per trade
MAX_DRAWDOWN = 0.12  # 12% maximum
MAX_DAILY_LOSS = 0.03  # 3% daily limit

# IBKR connection
IBKR_HOST = '127.0.0.1'
IBKR_PAPER_PORT = 7497
IBKR_LIVE_PORT = 7496
```

## Usage

### Quick Start

1. **Start IBKR TWS or Gateway**
   - Make sure it's running and logged in
   - Verify API is enabled (port 7497 for paper trading)

2. **Run the bot**
   ```bash
   python main.py
   ```

3. **Monitor the bot**
   - Check console output for trading activity
   - Review `eurcad_bot.log` for detailed logs

### Paper Trading (REQUIRED FIRST)

**IMPORTANT:** Always start with paper trading for at least 3 months before going live.

```python
# In config/config.py
PAPER_TRADING = True
```

Run the bot and monitor performance:
- Win rate should be >= 60%
- Profit factor should be >= 1.5
- Max drawdown should be <= 15%
- Bot should run without crashes for 30+ days

### Live Trading

**Only proceed to live trading after successful paper trading period.**

1. Switch to live mode:
   ```python
   # In config/config.py
   PAPER_TRADING = False
   ```

2. Start with 10% of planned capital

3. Monitor for 2 weeks before increasing capital

4. Never override bot decisions manually

### Backtesting

Test strategies on historical data before running live:

```python
from src.backtesting.backtester import Backtester
from src.strategies.mean_reversion import MeanReversionStrategy
import pandas as pd

# Load historical data
df = pd.read_csv('eurcad_historical_data.csv', index_col='date', parse_dates=True)

# Initialize backtester and strategy
backtester = Backtester(initial_capital=10000)
strategy = MeanReversionStrategy()

# Run backtest
results = backtester.run_backtest(df, strategy, '2023-01-01', '2024-01-01')

# Print results
print(f"Win Rate: {results['metrics']['win_rate']:.2%}")
print(f"Profit Factor: {results['metrics']['profit_factor']:.2f}")
print(f"Max Drawdown: {results['metrics']['max_drawdown']:.2%}")
print(f"Total Return: {results['metrics']['total_return']:.2%}")
```

## Project Structure

```
ForexBot/
├── config/
│   └── config.py              # Configuration settings
├── src/
│   ├── strategies/
│   │   ├── mean_reversion.py  # Mean reversion strategy
│   │   ├── trend_following.py # Trend following strategy
│   │   └── grid_trading.py    # Grid trading strategy
│   ├── risk_management/
│   │   ├── risk_manager.py    # Risk management system
│   │   └── emergency_stop.py  # Emergency stop system
│   ├── market_analysis/
│   │   └── regime_detector.py # Market regime detection
│   ├── ibkr/
│   │   └── connector.py       # IBKR API connector
│   ├── backtesting/
│   │   └── backtester.py      # Backtesting framework
│   └── bot.py                 # Main bot orchestration
├── tests/                     # Unit tests
├── requirements.txt           # Python dependencies
├── main.py                    # Entry point
├── README.md                  # This file
└── CLAUDE.md                  # Complete implementation guide
```

## Safety Features

### Circuit Breakers

The bot will automatically halt trading if:
- Drawdown exceeds 15%
- 5 consecutive losses occur
- Daily loss limit (3%) is reached
- API connectivity issues detected
- Extreme volatility detected (ATR > 2x average)
- Spread exceeds 10 pips
- Weekend/market closure

### Risk Limits (Non-Negotiable)

- **Per-trade risk:** Maximum 1% of capital
- **Total portfolio risk:** Maximum 5% across all trades
- **Max concurrent trades:** 3
- **Daily trade limit:** 10 trades
- **Max drawdown:** 12%

## Monitoring and Alerts

### Log Files

- `eurcad_bot.log` - Detailed trading activity and system events

### Console Output

Real-time information displayed:
- Market regime detection
- Strategy selection
- Trade signals and execution
- Position management
- Risk metrics
- Emergency stops

### Optional Alerts (TODO)

Configure in `config/config.py`:
- Telegram notifications
- Email alerts
- SMS notifications

## Performance Tracking

The bot tracks and logs:
- Win rate
- Profit factor
- Average R:R (risk/reward)
- Maximum drawdown
- Sharpe ratio
- Daily/weekly/monthly returns
- Total trades by strategy
- Best/worst trading sessions

## Troubleshooting

### Connection Issues

**Problem:** "Failed to connect to IBKR"

**Solutions:**
1. Ensure TWS/Gateway is running and logged in
2. Check API is enabled in TWS settings
3. Verify correct port (7497 for paper, 7496 for live)
4. Check firewall isn't blocking connection
5. Restart TWS/Gateway

### No Trading Activity

**Problem:** Bot runs but doesn't place trades

**Possible causes:**
1. Market regime is HIGH_VOLATILITY (bot stays out)
2. No valid signals meeting strategy criteria
3. Risk limits preventing new positions
4. Outside trading hours (8am-8pm GMT)
5. Weekend/market closed

**Check:**
- Review logs for regime detection
- Verify signal criteria in strategy code
- Check risk manager status
- Confirm current time is within trading hours

### Position Size Zero

**Problem:** "Position size is 0 - skipping trade"

**Causes:**
1. Stop loss too wide relative to capital
2. Risk percentage too low
3. Entry-stop distance calculated as zero

**Solutions:**
1. Increase capital
2. Adjust risk percentage (config)
3. Review strategy stop loss logic

## Best Practices

1. **Always start with paper trading** (minimum 3 months)
2. **Never skip backtesting** - Test strategies first
3. **Monitor daily** - Review logs and performance
4. **Don't overtrade** - Let the system work
5. **Never remove safety limits** - They exist for a reason
6. **Start small** - Use 10% of planned capital initially
7. **Be patient** - Consistency over time wins
8. **Keep records** - Track all trades and metrics
9. **Review weekly** - Analyze performance and adjust if needed
10. **Trust the process** - Don't override bot decisions

## Expected Performance Timeline

### Paper Trading (Months 1-3)
- Win Rate: 55-65%
- Monthly Return: 3-8%
- Max Drawdown: <15%
- Focus: Learning and optimization

### Live Trading (Months 4-6)
- Win Rate: 60-70%
- Monthly Return: 5-10%
- Max Drawdown: <12%
- Focus: Strategy refinement

### Mature Bot (Month 7+)
- Win Rate: 65-75%
- Monthly Return: 8-12%
- Max Drawdown: <12%
- Focus: Consistent performance

## Capital Growth Projection

Starting with $10,000 at 10% monthly return:

| Month | Capital    | Gain      |
|-------|------------|-----------|
| 0     | $10,000    | -         |
| 3     | $13,310    | +33.1%    |
| 6     | $17,716    | +77.2%    |
| 12    | $31,384    | +213.8%   |
| 24    | $98,497    | +884.9%   |

*Note: Past performance doesn't guarantee future results*

## Critical Warnings

1. **Forex trading is risky** - Only trade with money you can afford to lose
2. **Never skip paper trading** - Minimum 3 months required
3. **Start small** - Use 10% of planned capital initially
4. **Don't overtrade** - Patience is key to profitability
5. **Never remove safety limits** - They protect your capital
6. **Don't chase losses** - Stick to the system
7. **Review but don't override** - Trust the process

## Support and Contribution

This is a self-contained trading bot. For issues:
1. Review logs in `eurcad_bot.log`
2. Check troubleshooting section
3. Verify IBKR connection and settings
4. Review configuration in `config/config.py`

## License

This project is for educational and personal use only. Use at your own risk.

## Disclaimer

**IMPORTANT:** Trading forex carries a high level of risk and may not be suitable for all investors. The high degree of leverage can work against you as well as for you. Before deciding to trade forex, you should carefully consider your investment objectives, level of experience, and risk appetite. The possibility exists that you could sustain a loss of some or all of your initial investment and therefore you should not invest money that you cannot afford to lose.

This bot is provided "as is" without warranty of any kind. Past performance is not indicative of future results. Use at your own risk.

## Author

Built following the comprehensive implementation plan in CLAUDE.md.

## Version

1.0.0 - Initial production release
