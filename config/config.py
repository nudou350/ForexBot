"""
Configuration settings for EUR/CAD Trading Bot
"""

# IBKR Connection Settings
IBKR_HOST = '127.0.0.1'
IBKR_PAPER_PORT = 7497  # Paper trading
IBKR_LIVE_PORT = 7496   # Live trading
IBKR_CLIENT_ID = 1

# Trading Parameters
INITIAL_CAPITAL = 1000
PAPER_TRADING = True  # Start with paper trading

# Risk Management
MAX_RISK_PER_TRADE = 0.01  # 1% per trade
MAX_RISK_PER_TRADE_AGGRESSIVE = 0.015  # 1.5% for trend following
MAX_DRAWDOWN = 0.12  # 12% maximum drawdown
MAX_DAILY_LOSS = 0.03  # 3% maximum daily loss
MAX_CONCURRENT_TRADES = 3
MAX_DAILY_TRADES = 10
MAX_TOTAL_PORTFOLIO_RISK = 0.05  # 5% total risk

# Circuit Breakers
MAX_CONSECUTIVE_LOSSES = 5
HALT_ON_DRAWDOWN = 0.15  # 15% emergency stop

# Strategy Parameters
MEAN_REVERSION_RISK = 0.01
TREND_FOLLOWING_RISK = 0.015
GRID_TRADING_RISK = 0.008

# Market Regime Detection
ADX_STRONG_TREND_THRESHOLD = 30
ADX_WEAK_TREND_THRESHOLD = 20
ATR_HIGH_VOLATILITY_MULTIPLIER = 1.5
ATR_LOW_VOLATILITY_MULTIPLIER = 0.8
BB_WIDTH_BREAKOUT_MULTIPLIER = 0.7
BB_WIDTH_LOW_VOL_MULTIPLIER = 0.6

# Technical Indicators
EMA_FAST = 20
EMA_MEDIUM = 50
EMA_SLOW = 200
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2
ATR_PERIOD = 14
ADX_PERIOD = 14

# Position Management
TRAILING_STOP_ATR_MULTIPLE = 3
STOP_LOSS_ATR_MULTIPLE = 2
PARTIAL_PROFIT_PERCENTAGE = 0.5  # Close 50% at TP1

# EUR/CAD Specific
EURCAD_SYMBOL = 'EURCAD'
EURCAD_PIP_VALUE = 0.0001
EURCAD_TYPICAL_SPREAD_PIPS = 0.6
EURCAD_COMMISSION_PIPS = 0.6

# Data Settings
HISTORICAL_DATA_DURATION = '2 W'  # 2 weeks for analysis (increased from 5 days)
HISTORICAL_DATA_BARSIZE = '1 hour'  # 1-hour bars
MIN_DATA_POINTS = 200  # Minimum data points for analysis

# Trading Schedule (UTC hours)
TRADING_START_HOUR = 8   # 8 AM GMT (London open)
TRADING_END_HOUR = 20    # 8 PM GMT
AVOID_TRADING_WEEKENDS = True

# Logging
LOG_FILE = 'eurcad_bot.log'
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Dashboard (Optional)
ENABLE_DASHBOARD = True  # Auto-start dashboard with the bot
DASHBOARD_PORT = 8050
DASHBOARD_UPDATE_INTERVAL = 5000  # 5 seconds

# Backtesting
BACKTEST_TRAIN_PERIOD_MONTHS = 6
BACKTEST_TEST_PERIOD_MONTHS = 1
BACKTEST_COMMISSION_PIPS = 0.6

# Grid Trading Specific
GRID_SPACING_PIPS = 10
GRID_NUM_GRIDS = 10
GRID_CAPITAL_ALLOCATION = 0.7  # Use 70% of capital for grids

# Alert Settings (optional - implement as needed)
ENABLE_TELEGRAM_ALERTS = False
TELEGRAM_BOT_TOKEN = ''
TELEGRAM_CHAT_ID = ''

ENABLE_EMAIL_ALERTS = False
EMAIL_SMTP_SERVER = ''
EMAIL_SMTP_PORT = 587
EMAIL_FROM = ''
EMAIL_TO = ''
EMAIL_PASSWORD = ''
