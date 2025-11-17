# Reconnection Fix - Summary

## Problem
The bot was losing connection to IBKR after running for a day and entering an error spiral:
- **209+ API errors accumulated**
- **Trading halted** due to "Multiple API errors"
- **No automatic recovery** - bot stayed halted indefinitely
- **Error counter never reset** - kept growing infinitely

## Root Causes

1. **No Connection Health Monitoring**: Bot didn't check if connection was still alive
2. **No Reconnection Logic**: When connection dropped, bot never attempted to reconnect
3. **Poor Error Counter Design**: Total errors accumulated forever without reset
4. **No Auto-Resume**: Even if manually fixed, trading stayed halted

## Fixes Implemented

### 1. IBKR Connector (`src/ibkr/connector.py`)

#### Added Connection Health Checks
```python
def check_connection(self) -> bool:
    """Check if connection is still alive"""
    - Verifies IB API connection status
    - Tests with simple API request
    - Updates is_connected flag
```

#### Added Automatic Reconnection
```python
def reconnect(self) -> bool:
    """Attempt to reconnect with exponential backoff"""
    - Max 5 reconnection attempts
    - Exponential backoff: 5s, 10s, 15s, 20s, 30s
    - Logs all reconnection attempts
    - Resets reconnect counter on success
```

#### Added Connection Wrapper
```python
def ensure_connection(self) -> bool:
    """Ensure connection is alive, reconnect if necessary"""
    - Checks health first
    - Auto-reconnects if connection lost
    - Returns True only if connected
```

#### Updated get_historical_data()
- Now calls `ensure_connection()` before making API requests
- Automatically reconnects if connection was lost
- Marks as disconnected on errors for next cycle

### 2. Emergency Stop System (`src/risk_management/emergency_stop.py`)

#### Improved Error Tracking
```python
# OLD: Total errors only (accumulated forever)
self.api_error_count = 0

# NEW: Both total and consecutive tracking
self.api_error_count = 0          # Total (for monitoring)
self.consecutive_api_errors = 0   # Consecutive (for halt logic)
```

#### Smart Error Reset
```python
def reset_api_errors(self):
    # Only resets consecutive errors on success
    # Keeps total for monitoring/logging
    self.consecutive_api_errors = 0
```

#### Auto-Reset Protection
```python
# If total errors exceed 100, reset to consecutive count
# Prevents infinite accumulation
if self.api_error_count >= 100:
    self.api_error_count = self.consecutive_api_errors
```

#### Updated Halt Logic
```python
# OLD: Halt on total >= 3
if self.api_error_count >= 3:

# NEW: Halt on consecutive >= 3
if self.consecutive_api_errors >= 3:
```

### 3. Main Bot (`src/bot.py`)

#### Auto-Resume Trading
```python
# After successful data fetch, check if we can resume
if (trading_halted and
    halt_reason == "Multiple consecutive API errors"):

    # Connection restored and data received
    resume_trading()
    log("✅ Connection restored. Resuming trading...")
```

## How It Works Now

### Normal Operation
1. Bot tries to fetch historical data
2. `get_historical_data()` calls `ensure_connection()`
3. Connection check passes → data fetched successfully
4. Consecutive errors reset to 0
5. Trading continues normally

### Connection Loss Scenario
1. IB Gateway disconnects/crashes
2. `get_historical_data()` detects lost connection
3. **Auto-reconnection triggered**:
   - Attempt 1: Wait 5s, try to connect
   - Attempt 2: Wait 10s, try to connect
   - Attempt 3: Wait 15s, try to connect
   - Attempt 4: Wait 20s, try to connect
   - Attempt 5: Wait 30s, try to connect
4. **If reconnection succeeds**:
   - Fetches data successfully
   - Resets consecutive errors to 0
   - **Auto-resumes trading** if it was halted
   - Bot continues normally
5. **If all reconnections fail**:
   - Logs error
   - Consecutive errors increment
   - After 3 consecutive failures → trading halts
   - Next cycle will try reconnecting again

### Recovery from Halted State
- **OLD**: Bot stayed halted forever, required manual intervention
- **NEW**: Automatically resumes when:
  1. Connection is restored
  2. Data is successfully fetched
  3. Halt reason was API errors

## Benefits

✅ **Automatic Recovery**: No manual intervention needed for connection issues
✅ **Persistent**: Keeps trying to reconnect across multiple cycles
✅ **Smart Error Tracking**: Distinguishes between transient and persistent errors
✅ **No Error Spiral**: Consecutive errors reset on success
✅ **Auto-Resume**: Trading resumes automatically when connection restored
✅ **Exponential Backoff**: Doesn't spam reconnection attempts
✅ **Monitoring**: Still logs total errors for analysis

## Testing

### Test Script
Run `python test_reconnection.py` to verify:
1. Initial connection works
2. Connection health checks work
3. Data fetching works
4. Reconnection after disconnect works
5. Data fetching after reconnection works

### Manual Testing on VPS
1. Deploy the fixes
2. Stop IB Gateway while bot is running
3. Watch logs - should see reconnection attempts
4. Restart IB Gateway
5. Bot should reconnect and resume trading

## Deployment to VPS

### Option 1: Git Pull (Recommended)
```bash
ssh user@your-vps
cd /path/to/ForexBot
git pull origin main
pkill -f "python.*main.py"
sleep 5
nohup python3 main.py > bot_output.log 2>&1 &
```

### Option 2: Manual File Upload
```bash
# From your local machine
scp src/ibkr/connector.py user@vps:/path/to/ForexBot/src/ibkr/
scp src/risk_management/emergency_stop.py user@vps:/path/to/ForexBot/src/risk_management/
scp src/bot.py user@vps:/path/to/ForexBot/src/

# Then SSH to VPS and restart
ssh user@vps
cd /path/to/ForexBot
pkill -f "python.*main.py"
sleep 5
nohup python3 main.py > bot_output.log 2>&1 &
```

### Option 3: Use the Update Script
```bash
# On VPS
cd /path/to/ForexBot
chmod +x update_vps.sh
./update_vps.sh
```

## Monitoring

### Check if reconnection is working
```bash
# Watch the logs in real-time
tail -f eurcad_bot.log

# Look for these messages:
# - "Connection check failed"
# - "Attempting to reconnect to IBKR..."
# - "Reconnection attempt X/5"
# - "Reconnection successful!"
# - "Connection restored. Resetting consecutive errors"
# - "✅ Connection restored. Resuming trading..."
```

### Check error counts
```bash
# In logs, you'll now see:
# "API error logged. Consecutive: X, Total: Y"
# - Consecutive should reset to 0 on success
# - Total can grow but auto-resets at 100
```

## Expected Behavior

### Before Fix
```
[11:28:54] ERROR - Error fetching historical data: Not connected
[11:28:54] WARNING - Insufficient data
[11:28:54] ERROR - API error logged. Total errors: 209
[11:28:54] CRITICAL - TRADING HALTED: Multiple API errors
[11:29:54] ERROR - Error fetching historical data: Not connected
[11:29:54] WARNING - Insufficient data
[11:29:54] ERROR - API error logged. Total errors: 210
[11:29:54] CRITICAL - TRADING HALTED: Multiple API errors
... (continues forever)
```

### After Fix
```
[11:28:54] WARNING - Connection check failed: not connected
[11:28:54] WARNING - Attempting to reconnect to IBKR...
[11:28:54] INFO - Reconnection attempt 1/5 (waiting 5s)...
[11:28:59] INFO - Connected to IBKR on 127.0.0.1:7497
[11:28:59] INFO - Reconnection successful!
[11:28:59] INFO - Fetched 120 bars of historical data
[11:28:59] INFO - Connection restored. Resetting consecutive errors from 3. Total errors: 209
[11:28:59] INFO - Connection restored and data received. Auto-resuming trading...
[11:28:59] INFO - Trading resumed
[11:28:59] INFO - Market regime: RANGING
... (continues normally)
```

## Configuration

### Adjustable Parameters

In `src/ibkr/connector.py`:
```python
self.max_reconnect_attempts = 5  # Max reconnection attempts per cycle
# Backoff timing: min(30, 5 * attempt_number) seconds
```

In `src/risk_management/emergency_stop.py`:
```python
self.max_consecutive_errors = 3      # Halt after 3 consecutive errors
self.error_reset_threshold = 100     # Auto-reset total errors at 100
```

## Notes

- Reconnection happens **every cycle** (every 60 seconds) when connection is lost
- The bot won't give up after 5 failed attempts - it resets the counter each cycle
- This means it will keep trying indefinitely until:
  1. Connection is restored, OR
  2. You manually stop the bot
- Total error count is for monitoring only - doesn't affect halt logic
- Only consecutive errors trigger trading halt
- Trading auto-resumes only for API error halts (not for other halt reasons like drawdown)

## Troubleshooting

### Bot still not reconnecting?
1. Check IB Gateway is running: `ps aux | grep gateway`
2. Check port configuration in `config.py`
3. Verify firewall allows connection
4. Check logs for specific error messages

### Bot reconnects but trading doesn't resume?
1. Check halt reason in logs
2. Only API error halts auto-resume
3. Other halts (drawdown, volatility) require manual resume
4. Verify `resume_trading()` is being called

### Errors still accumulating?
1. Check `consecutive_api_errors` vs `api_error_count` in logs
2. Consecutive should reset to 0 on successful data fetch
3. Total can grow but should reset at 100
4. If consecutive never resets, connection isn't being restored

## Success Criteria

✅ Bot automatically reconnects when IB Gateway restarts
✅ Trading resumes automatically after reconnection
✅ No infinite error accumulation
✅ Logs show clear reconnection attempts and success
✅ Bot can run for days/weeks without intervention

---

**Status**: ✅ **READY FOR DEPLOYMENT**

Last Updated: 2025-11-17
Version: 1.1.0 (Reconnection Fix)
