# Deployment Guide - VPS Update

## ✅ Pre-Deployment Verification

Run this command to verify everything works locally:
```bash
python pre_deploy_check.py
```

Expected output: `✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT`

---

## 📦 Files Changed

The following files have been updated with reconnection logic:

1. **src/ibkr/connector.py**
   - Added asyncio event loop fix for Python 3.14+
   - Added `check_connection()` method
   - Added `reconnect()` method with exponential backoff
   - Added `ensure_connection()` wrapper
   - Updated `get_historical_data()` to auto-reconnect

2. **src/risk_management/emergency_stop.py**
   - Added `consecutive_api_errors` tracking
   - Added `max_consecutive_errors` limit
   - Added `error_reset_threshold` for auto-reset
   - Updated `log_api_error()` with smart tracking
   - Updated `reset_api_errors()` to only reset consecutive

3. **src/bot.py**
   - Added auto-resume logic after reconnection
   - Improved connection state handling

---

## 🚀 Deployment Steps

### Option 1: Git Pull (Recommended)

If your VPS has git configured:

```bash
# 1. SSH to your VPS
ssh user@your-vps-ip

# 2. Navigate to bot directory
cd /path/to/ForexBot

# 3. Stop the currently running bot
pkill -f "python.*main.py"

# 4. Wait for process to stop
sleep 5

# 5. Pull latest changes
git pull origin main

# 6. Verify changes
python3 pre_deploy_check.py

# 7. Start bot with new reconnection logic
nohup python3 main.py > bot_output.log 2>&1 &

# 8. Verify it's running
ps aux | grep "python.*main.py"

# 9. Watch logs for reconnection messages
tail -f eurcad_bot.log
```

### Option 2: Manual File Upload (SCP)

If you can't use git on VPS:

```bash
# From your local machine (Windows/WSL)

# 1. Upload updated files
scp src/ibkr/connector.py user@vps:/path/to/ForexBot/src/ibkr/
scp src/risk_management/emergency_stop.py user@vps:/path/to/ForexBot/src/risk_management/
scp src/bot.py user@vps:/path/to/ForexBot/src/

# Optional: Upload test scripts
scp pre_deploy_check.py user@vps:/path/to/ForexBot/
scp test_syntax.py user@vps:/path/to/ForexBot/

# 2. SSH to VPS
ssh user@vps

# 3. Navigate to bot directory
cd /path/to/ForexBot

# 4. Verify upload worked
python3 pre_deploy_check.py

# 5. Stop current bot
pkill -f "python.*main.py"

# 6. Wait and restart
sleep 5
nohup python3 main.py > bot_output.log 2>&1 &

# 7. Verify
ps aux | grep "python.*main.py"
tail -f eurcad_bot.log
```

### Option 3: Quick Update Script

```bash
# On VPS, create update script
cat > update_bot.sh << 'EOF'
#!/bin/bash
echo "Stopping bot..."
pkill -f "python.*main.py"
sleep 5

echo "Pulling changes..."
git pull origin main

echo "Running checks..."
python3 pre_deploy_check.py

if [ $? -eq 0 ]; then
    echo "Starting bot..."
    nohup python3 main.py > bot_output.log 2>&1 &
    sleep 2
    echo "Bot status:"
    ps aux | grep "python.*main.py" | grep -v grep
    echo ""
    echo "Watching logs (Ctrl+C to exit)..."
    tail -f eurcad_bot.log
else
    echo "Pre-deployment checks failed! Bot not started."
    exit 1
fi
EOF

# Make executable
chmod +x update_bot.sh

# Run update
./update_bot.sh
```

---

## 🔍 Verification Steps

After deployment, verify the fix is working:

### 1. Check Bot is Running
```bash
ps aux | grep "python.*main.py" | grep -v grep
```

Should show the python process running.

### 2. Check Initial Connection
```bash
tail -20 eurcad_bot.log
```

Should see:
```
Connected to IBKR on 127.0.0.1:7497
Fetched 120 bars of historical data
Market regime: RANGING
```

### 3. Test Reconnection (Optional)

To test reconnection logic:

```bash
# Find IB Gateway process
ps aux | grep gateway

# Kill IB Gateway (simulates disconnect)
pkill -9 -f gateway

# Watch logs - should see reconnection attempts
tail -f eurcad_bot.log
```

Expected log output:
```
WARNING - Connection check failed
WARNING - Attempting to reconnect to IBKR...
INFO - Reconnection attempt 1/5 (waiting 5s)...
INFO - Reconnection attempt 2/5 (waiting 10s)...
INFO - Connected to IBKR on 127.0.0.1:7497
INFO - Reconnection successful!
INFO - Connection restored. Resetting consecutive errors from 3. Total errors: X
INFO - ✅ Connection restored. Resuming trading...
INFO - Trading resumed
```

### 4. Check Error Tracking

```bash
grep "API error logged" eurcad_bot.log | tail -5
```

Should show new format:
```
API error logged. Consecutive: 1, Total: 1
API error logged. Consecutive: 2, Total: 2
Connection restored. Resetting consecutive errors from 2. Total errors: 2
```

### 5. Monitor for 24 Hours

```bash
# Check logs every few hours
watch -n 3600 'tail -20 eurcad_bot.log'
```

Look for:
- ✅ No infinite error accumulation
- ✅ Automatic reconnections working
- ✅ Trading resuming after reconnection
- ✅ No manual intervention needed

---

## 📊 Expected Behavior

### Before Fix
```
[11:28:54] ERROR - Not connected
[11:28:54] ERROR - API error logged. Total errors: 209
[11:28:54] CRITICAL - TRADING HALTED
[11:29:54] ERROR - Not connected
[11:29:54] ERROR - API error logged. Total errors: 210
... (repeats forever, requires manual intervention)
```

### After Fix
```
[11:28:54] WARNING - Connection check failed
[11:28:54] WARNING - Attempting to reconnect...
[11:28:59] INFO - Reconnection attempt 1/5
[11:29:04] INFO - Reconnection attempt 2/5
[11:29:09] INFO - Connected to IBKR
[11:29:09] INFO - Reconnection successful!
[11:29:09] INFO - ✅ Connection restored. Resuming trading...
[11:29:09] INFO - Market regime: RANGING
... (continues normally)
```

---

## 🚨 Troubleshooting

### Issue: Bot won't start after update

**Check Python version:**
```bash
python3 --version
```
Should be Python 3.8+

**Check dependencies:**
```bash
pip3 list | grep ib-insync
```
Should show ib-insync installed.

**Check for syntax errors:**
```bash
python3 pre_deploy_check.py
```

### Issue: Bot starts but immediately stops

**Check logs:**
```bash
tail -50 eurcad_bot.log
```

**Check output log:**
```bash
cat bot_output.log
```

**Common causes:**
- IB Gateway not running
- Port conflict (another bot instance running)
- Config file issues

### Issue: Reconnection not working

**Verify IB Gateway is running:**
```bash
ps aux | grep gateway
netstat -tuln | grep 7497
```

**Check connector has new methods:**
```bash
python3 -c "from src.ibkr.connector import IBKRConnector; c = IBKRConnector(); print('Has reconnect:', hasattr(c, 'reconnect'))"
```

Should output: `Has reconnect: True`

### Issue: Errors still accumulating

**Check which counter is growing:**
```bash
grep "API error logged" eurcad_bot.log | tail -20
```

- If **consecutive** keeps growing → connection not being restored
- If only **total** grows but consecutive resets → working correctly

**Verify reset logic:**
```bash
grep "Resetting consecutive errors" eurcad_bot.log
```

Should see resets when connection restored.

---

## 📈 Success Metrics

After 24-48 hours, you should see:

✅ **No manual interventions** needed
✅ **Consecutive errors** reset to 0 after successful reconnections
✅ **Trading auto-resumes** after connection restored
✅ **Bot runs continuously** without halting permanently
✅ **Reconnection logs** show successful recovery

---

## 🔄 Rollback Plan

If the update causes issues:

```bash
# Stop bot
pkill -f "python.*main.py"

# Rollback git changes
git reset --hard HEAD~1

# Or restore old files from backup
cp backup/connector.py src/ibkr/
cp backup/emergency_stop.py src/risk_management/
cp backup/bot.py src/

# Restart
nohup python3 main.py > bot_output.log 2>&1 &
```

---

## 📞 Support

If you encounter issues:

1. Check logs: `tail -100 eurcad_bot.log`
2. Run diagnostics: `python3 pre_deploy_check.py`
3. Test reconnection: `python3 test_syntax.py`
4. Check IB Gateway status
5. Verify firewall/network connectivity

---

## ✅ Deployment Checklist

- [ ] Ran `pre_deploy_check.py` locally - all passed
- [ ] Stopped current bot on VPS
- [ ] Pulled/uploaded new files to VPS
- [ ] Ran `pre_deploy_check.py` on VPS - all passed
- [ ] Started bot on VPS
- [ ] Verified bot is running (ps aux)
- [ ] Checked logs - bot connected successfully
- [ ] Tested reconnection logic (optional)
- [ ] Monitoring for 24 hours
- [ ] No manual interventions needed

---

**Last Updated:** 2025-11-17
**Version:** 1.1.0 (Reconnection Fix)
**Status:** ✅ READY FOR PRODUCTION
