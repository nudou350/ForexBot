# EUR/CAD Trading Bot - Quick Start Guide

## Step-by-Step Setup (15 minutes)

### 1. Prerequisites Check

Before starting, ensure you have:

- [ ] Python 3.8 or higher installed
- [ ] Interactive Brokers account (paper trading is fine to start)
- [ ] IBKR TWS or Gateway installed
- [ ] Basic understanding of forex trading

### 2. Install Dependencies (2 minutes)

```bash
cd E:\Projetos\ForexBot
pip install -r requirements.txt
```

Expected output: All packages installed successfully

### 3. Configure IBKR TWS/Gateway (5 minutes)

#### Enable API Access:

1. Open IBKR TWS or Gateway
2. Log in to your account (paper trading or live)
3. Go to: **File > Global Configuration > API > Settings**
4. Configure:
   - ✓ Enable ActiveX and Socket Clients
   - Set Socket port to **7497** (paper) or **7496** (live)
   - ✓ Allow connections from localhost
   - ✗ Read-Only API (UNCHECK this)
   - Set Master API client ID: **0**
5. Click **OK** and restart TWS/Gateway

#### Verify Connection:

- TWS should show a green "API" indicator in the top-right corner
- Port should be listening (7497 for paper, 7496 for live)

### 4. Configure the Bot (2 minutes)

Edit `config/config.py`:

```python
# Start with paper trading (REQUIRED)
PAPER_TRADING = True

# Set your starting capital
INITIAL_CAPITAL = 10000  # $10,000

# Risk settings (conservative defaults)
MAX_RISK_PER_TRADE = 0.01  # 1% per trade
MAX_DRAWDOWN = 0.12  # 12%
MAX_DAILY_LOSS = 0.03  # 3%

# IBKR connection (usually no need to change)
IBKR_HOST = '127.0.0.1'
IBKR_PAPER_PORT = 7497  # Paper trading
IBKR_LIVE_PORT = 7496   # Live trading (use only after 3+ months paper)
```

### 5. Test the Setup (3 minutes)

Run the test suite to verify everything works:

```bash
python tests/test_strategies.py
```

Expected output:
```
============================================================
ALL TESTS PASSED
============================================================
```

If you see "ALL TESTS PASSED", you're ready to proceed!

### 6. Run Your First Backtest (3 minutes)

Test strategies on historical data:

```bash
python examples/backtest_example.py
```

This will:
- Generate sample EUR/CAD data
- Test Mean Reversion strategy
- Test Trend Following strategy
- Run walk-forward analysis
- Show performance metrics

Review the results to understand how the strategies perform.

### 7. Start Paper Trading (REQUIRED - 3 months minimum)

**CRITICAL: Never skip this step. Always paper trade for at least 3 months.**

1. Ensure TWS/Gateway is running
2. Verify you're in paper trading mode
3. Start the bot:

```bash
python main.py
```

Expected output:
```
╔═══════════════════════════════════════╗
║   EUR/CAD TRADING BOT - STARTED      ║
║                                       ║
║   Platform: Interactive Brokers      ║
║   Mode: PAPER TRADING                ║
║   Initial Capital: $10,000.00        ║
║                                       ║
║   Target: 65-75% Win Rate            ║
║   Max Drawdown: 12%                  ║
║                                       ║
║   Press Ctrl+C to stop               ║
╚═══════════════════════════════════════╝

Connected to IBKR on port 7497
```

### 8. Monitor the Bot

The bot will:
- Analyze market every minute
- Detect market regime (STRONG_TREND, RANGING, etc.)
- Select appropriate strategy
- Generate trade signals when conditions are met
- Execute trades automatically
- Manage positions with stop-loss and take-profit
- Log all activity to `eurcad_bot.log`

**Console Output Example:**
```
Market regime: RANGING
Active strategy: mean_reversion

LONG position opened:
  Size: 0.50 lots
  Entry: 1.45250
  Stop Loss: 1.45100
  Take Profit: 1.45400
  Risk/Reward: 2.00:1
```

### 9. Daily Monitoring Routine (5 minutes/day)

Every day:

1. **Check the bot is running**
   - Verify TWS/Gateway is connected
   - Confirm bot console shows recent activity

2. **Review logs**
   ```bash
   tail -50 eurcad_bot.log
   ```

3. **Check performance**
   - Win rate (target: 60%+)
   - Daily P&L
   - Current drawdown (must be <12%)
   - Open positions

4. **Verify safety systems**
   - No emergency halts
   - Risk limits being respected
   - Stop losses in place

### 10. Weekly Review (15 minutes/week)

Every week:

1. **Calculate metrics**
   - Weekly win rate
   - Profit factor
   - Average R:R ratio
   - Max drawdown

2. **Review trades**
   - Which strategy performed best?
   - Any patterns in losses?
   - Are stops being hit frequently?

3. **Check system health**
   - API connection stable?
   - Any errors in logs?
   - Bot running continuously?

4. **Document observations**
   - Keep a trading journal
   - Note market conditions
   - Track any issues

## Common Issues and Solutions

### Issue: "Failed to connect to IBKR"

**Solutions:**
1. Verify TWS/Gateway is running and logged in
2. Check API is enabled (see step 3)
3. Confirm correct port (7497 for paper, 7496 for live)
4. Restart TWS/Gateway
5. Check firewall isn't blocking connection

### Issue: Bot runs but no trades

**Possible causes:**
1. Market regime is HIGH_VOLATILITY (bot stays out for safety)
2. No valid signals meeting strict entry criteria
3. Risk limits preventing new positions
4. Outside trading hours (8am-8pm GMT)
5. Weekend/market closed

**Check:**
```bash
# Review recent logs
tail -100 eurcad_bot.log | grep -E "regime|signal|position"
```

### Issue: "Position size is 0"

**Causes:**
1. Stop loss too wide relative to capital
2. Risk percentage too low
3. Insufficient capital for minimum trade size

**Solutions:**
1. Increase initial capital in config
2. Review strategy stop loss calculations
3. Ensure capital > $5,000 minimum

### Issue: Bot stopped unexpectedly

**Check:**
1. Review `eurcad_bot.log` for errors
2. Verify TWS/Gateway didn't disconnect
3. Check if emergency stop triggered:
   - Drawdown limit reached
   - Daily loss limit hit
   - 5 consecutive losses
   - API errors

**Resume:**
- Fix the underlying issue
- Restart the bot
- Monitor closely

## Performance Expectations

### First Month (Paper Trading)
- **Win Rate:** 50-60% (learning phase)
- **Monthly Return:** 2-5%
- **Trades:** 20-40
- **Focus:** System stability

### Months 2-3 (Paper Trading)
- **Win Rate:** 55-65%
- **Monthly Return:** 4-8%
- **Trades:** 30-60
- **Focus:** Strategy optimization

### Months 4+ (Consider Live Trading)
- **Win Rate:** 60-70%
- **Monthly Return:** 6-10%
- **Trades:** 40-80
- **Focus:** Consistency

## When to Go Live

Only proceed to live trading when ALL conditions are met:

- [ ] Paper trading for 3+ months
- [ ] Win rate >= 60%
- [ ] Profit factor >= 1.5
- [ ] Max drawdown <= 15%
- [ ] Bot runs without crashes for 30+ days
- [ ] No manual intervention needed
- [ ] You understand how the bot works
- [ ] You're comfortable with the risk

## Live Trading Transition

**When ready:**

1. **Start small** - Use 10% of planned capital
2. **Update config:**
   ```python
   PAPER_TRADING = False
   INITIAL_CAPITAL = 1000  # Start with $1,000
   ```
3. **Monitor closely** - Watch every trade for 2 weeks
4. **Gradually increase** - Add capital only if performing well
5. **Never override** - Don't manually interfere with bot decisions

## Safety Reminders

1. **Never skip paper trading** - 3 months minimum
2. **Start small in live** - 10% of planned capital
3. **Monitor daily** - Don't set and forget
4. **Respect stop losses** - They protect your capital
5. **Review weekly** - Track performance metrics
6. **Keep logs** - Document everything
7. **Don't overtrade** - Let the system work
8. **Be patient** - Consistency over time wins

## Getting Help

If you encounter issues:

1. **Check logs first**
   ```bash
   cat eurcad_bot.log
   ```

2. **Review troubleshooting section** above

3. **Verify IBKR connection**
   - TWS/Gateway running?
   - API enabled?
   - Correct port?

4. **Test components individually**
   ```bash
   python tests/test_strategies.py
   ```

5. **Review configuration**
   - Check `config/config.py` settings
   - Verify capital and risk limits

## Next Steps

After completing setup:

1. ✓ Run tests (`python tests/test_strategies.py`)
2. ✓ Run backtest example (`python examples/backtest_example.py`)
3. ✓ Start paper trading (`python main.py`)
4. ✓ Monitor daily (logs, console, TWS)
5. ✓ Review weekly (performance, metrics, issues)
6. ✓ Continue for 3+ months
7. ✓ Only then consider live trading

## Support

For detailed documentation, see:
- `README.md` - Complete documentation
- `CLAUDE.md` - Full implementation guide
- `config/config.py` - All configuration options
- `eurcad_bot.log` - Trading activity logs

## Important Disclaimers

- **Forex trading is risky** - Only trade with money you can afford to lose
- **No guarantees** - Past performance doesn't indicate future results
- **Use at your own risk** - This bot is provided as-is
- **Paper trade first** - Always test thoroughly before live trading
- **Start small** - Never risk more than you can afford to lose

---

**Ready to start? Run:**
```bash
python main.py
```

**Good luck and trade responsibly!**
