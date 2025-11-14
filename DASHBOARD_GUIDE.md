# EUR/CAD Trading Bot - Dashboard Guide

## Overview

The real-time web dashboard lets you monitor your trading bot's performance through a beautiful web interface that auto-updates every 5 seconds.

## What the Dashboard Shows

### 📊 Key Metrics (Top Row)
- **Current Capital**: Your account balance in real-time
- **Win Rate**: Percentage of winning trades
- **Total Trades**: Number of completed trades
- **Open Positions**: Currently active trades

### 🎯 Strategy Info (Second Row)
- **Market Regime**: Current market condition (STRONG_TREND, RANGING, etc.)
- **Active Strategy**: Which strategy is currently running (Mean Reversion, Trend Following, Grid)
- **Bot Status**: Running or Halted

### 📈 Charts
- **Equity Curve**: Visual representation of your account growth over time
- **Win/Loss Pie Chart**: Distribution of winning vs losing trades

### 📋 Recent Trades Table
Shows your last 10 trades with:
- Entry and exit times
- Trade type (LONG/SHORT)
- Entry and exit prices
- Profit/Loss for each trade
- Win/Loss indicator

---

## How to Use the Dashboard

### Step 1: Start the Bot First
```bash
python main.py
```

The bot **must be running** for the dashboard to have data to display.

### Step 2: Launch the Dashboard (in a new terminal)
```bash
python run_dashboard.py
```

### Step 3: Open Your Browser
Go to: **http://localhost:8050**

The dashboard will automatically:
- ✅ Refresh every 5 seconds
- ✅ Show live capital updates
- ✅ Display new trades as they happen
- ✅ Update charts in real-time

---

## Dashboard Features

### Auto-Refresh
- Updates every **5 seconds** automatically
- No need to manually refresh the page
- Shows "Last updated" timestamp

### Responsive Design
- Works on desktop and tablet
- Clean, professional interface
- Color-coded metrics (green for profit, red for loss)

### Real-Time Data
The dashboard reads from `bot_state.json` which the bot updates every trading cycle (60 seconds).

---

## Troubleshooting

### Dashboard shows "No data available"
**Solution**: Make sure the bot is running (`python main.py`)

### Dashboard not updating
**Solutions**:
1. Check that `bot_state.json` exists in the project folder
2. Verify the bot is actively trading (check logs)
3. Refresh your browser (Ctrl+F5)

### Can't access http://localhost:8050
**Solutions**:
1. Check if dashboard is actually running
2. Try http://127.0.0.1:8050 instead
3. Make sure no other app is using port 8050

### Bot running but no trades showing
**Normal behavior**: The bot waits for proper entry signals. It may take hours or days before conditions are met for a trade.

---

## Port Configuration

Default port: **8050**

To change the port, edit `run_dashboard.py`:
```python
dashboard = TradingDashboard(port=9000)  # Use port 9000 instead
```

---

## Stopping the Dashboard

Press **Ctrl+C** in the terminal where the dashboard is running.

**Note**: This does NOT stop the trading bot. The bot runs independently.

---

## Running Both Together

**Terminal 1 - Bot:**
```bash
python main.py
```

**Terminal 2 - Dashboard:**
```bash
python run_dashboard.py
```

**Browser:**
Open http://localhost:8050

---

## What You Should See

When everything is working:

```
=========================================
   EUR/CAD BOT DASHBOARD STARTED
=========================================
   Open your browser and go to:
   http://localhost:8050

   Dashboard will auto-refresh every 5s
   Press Ctrl+C to stop
=========================================

 * Serving Flask app 'dashboard'
 * Running on http://0.0.0.0:8050
```

Then in your browser, you'll see:
- Live capital balance
- Win rate percentage
- Market regime and active strategy
- Beautiful equity curve chart
- Recent trades table

---

## Tips for Best Experience

1. **Use two monitors**: Bot terminal on one, dashboard browser on the other
2. **Keep browser tab open**: Dashboard only updates when the page is open
3. **Check daily**: Monitor performance daily but don't interfere with the bot
4. **Export data**: You can inspect `bot_state.json` for raw data

---

## Data Persistence

- Trade history is stored in `bot_state.json`
- Log file: `eurcad_bot.log` contains detailed logs
- Data resets when bot restarts (by design for paper trading)

---

## Security Note

The dashboard runs on **localhost only** (0.0.0.0:8050 for local network access).

To restrict to localhost only, edit `dashboard.py`:
```python
self.app.run_server(debug=False, port=self.port, host='127.0.0.1')
```

---

## Enjoy Monitoring Your Bot! 🚀

The dashboard makes it easy to track performance without constantly checking log files. Let it run, check it daily, and watch your EUR/CAD bot trade!
