# EUR/CAD Trading Bot - Troubleshooting Guide

## Issue: "Error 366 - No Historical Data"

### Symptoms
```
Error 366: No historical data query found for ticker id
Market data farm connection is inactive
reqHistoricalData: Timeout
TRADING HALTED: Multiple API errors
```

### Root Cause
IBKR Paper Trading accounts don't automatically include forex market data subscriptions.

---

## Solution: Enable Forex Market Data Subscriptions

### Method 1: Through IBKR Account Management (Recommended)

**Step 1: Log into Account Management**
1. Go to: https://www.interactivebrokers.com
2. Click **Login** → **Account Management**
3. Enter your username and password

**Step 2: Subscribe to Forex Market Data**
1. Click **Settings** (gear icon)
2. Click **User Settings**
3. Click **Market Data Subscriptions**
4. Look for **"Forex Market Data"** or **"Ideal Market Data"**
5. Click **Subscribe** (it's FREE for non-professional traders)
6. Accept the agreement
7. Click **Submit**

**Step 3: Restart TWS**
1. Close TWS/Gateway completely
2. Wait 2 minutes for subscription to activate
3. Restart TWS/Gateway
4. Run the bot again

---

### Method 2: Through TWS Application

**Step 1: In TWS**
1. Go to **Account** → **Market Data Subscriptions**
2. Look for available subscriptions

**Step 2: Request Market Data**
1. If you see forex market data, click **Subscribe**
2. If not available in TWS, use Method 1 (Account Management)

---

## Verify Market Data is Working

### Test 1: Check in TWS
1. In TWS, create a watchlist
2. Add symbol: **EUR.USD** (Forex)
3. You should see **live prices updating**
4. If you see "Delayed" or blank prices, subscription isn't active

### Test 2: Manual Historical Data Request
In TWS:
1. Right-click EUR.USD
2. Select **Chart**
3. If you see a price chart → Market data is working ✅
4. If you see errors → Subscription needed ❌

---

## Alternative: Use Simulated Data (Testing Only)

If you want to test the bot without market data subscriptions, you can run backtests using simulated data:

```bash
# Run backtest with generated data
python examples/backtest_example.py
```

This will test strategies on historical patterns without needing live market data.

---

## Still Not Working?

### Check 1: Market Hours
Forex market is **closed on weekends**:
- Opens: Sunday 5:00 PM EST
- Closes: Friday 5:00 PM EST

**Current time**: Check if market is open

### Check 2: Paper Trading Account Status
Some paper trading accounts have limitations:
1. Log into IBKR Account Management
2. Go to **Account Settings** → **Paper Trading**
3. Verify account is **active** and **funded**

### Check 3: TWS API Settings
Verify API is properly configured:
1. **File** → **Global Configuration** → **API** → **Settings**
2. Check:
   - ✅ Enable ActiveX and Socket Clients
   - ✅ Port 7497 (paper trading)
   - ✅ Allow connections from localhost
   - ❌ Read-Only API (should be UNCHECKED)

### Check 4: Firewall/Antivirus
Some firewalls block API connections:
1. Add TWS to firewall exceptions
2. Add Python to firewall exceptions
3. Temporarily disable antivirus to test

---

## Expected Behavior After Fix

Once market data is enabled, you should see:

```log
Connected to IBKR on 127.0.0.1:7497
Fetched 200+ bars of historical data
Market regime: RANGING
Active strategy: mean_reversion
```

The bot will then monitor the market and generate signals when conditions are met.

---

## Important Notes

1. **Market data subscriptions may take 5-10 minutes to activate**
   - Be patient after subscribing
   - Restart TWS after subscribing

2. **Forex market data is FREE for non-professional traders**
   - You should not be charged
   - If asked to pay, you may have selected wrong subscription tier

3. **Paper trading has same data as live**
   - Once subscribed, paper account gets same market data
   - No difference in data quality

4. **The bot's safety system is working correctly**
   - It halted trading when data wasn't available
   - This protected you from blind trading
   - This is the expected behavior ✅

---

## Contact Support

If none of these solutions work:

**IBKR Support:**
- Chat: https://www.interactivebrokers.com/en/support/contact.php
- Phone: Check your region on IBKR website
- Ask about: "Enabling forex market data for paper trading account"

**Bot Issues:**
- Check `eurcad_bot.log` for detailed error messages
- Review configuration in `config/config.py`
- Ensure TWS is running before starting the bot
