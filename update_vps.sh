#!/bin/bash

# Update VPS with reconnection fixes
# Run this script to deploy the fixes to your VPS

echo "=== Updating EUR/CAD Trading Bot on VPS ==="
echo ""

# Check if we're on VPS or local
if [ -f "/etc/os-release" ]; then
    echo "Detected Linux system (likely VPS)"
    ON_VPS=true
else
    echo "Detected Windows system (local development)"
    ON_VPS=false
fi

# If on VPS, just restart the bot
if [ "$ON_VPS" = true ]; then
    echo "Stopping bot..."
    pkill -f "python.*main.py" || echo "Bot not running"

    echo "Waiting 5 seconds..."
    sleep 5

    echo "Starting bot with new reconnection logic..."
    nohup python3 main.py > bot_output.log 2>&1 &

    echo "Bot restarted. Check logs with: tail -f eurcad_bot.log"
    echo ""
    echo "✅ Update complete!"
else
    echo ""
    echo "To update your VPS, run these commands on your VPS via SSH:"
    echo ""
    echo "  cd /path/to/ForexBot"
    echo "  git pull origin main"
    echo "  pkill -f 'python.*main.py'"
    echo "  sleep 5"
    echo "  nohup python3 main.py > bot_output.log 2>&1 &"
    echo ""
    echo "Or upload the updated files via SCP:"
    echo ""
    echo "  scp src/ibkr/connector.py user@vps:/path/to/ForexBot/src/ibkr/"
    echo "  scp src/risk_management/emergency_stop.py user@vps:/path/to/ForexBot/src/risk_management/"
    echo "  scp src/bot.py user@vps:/path/to/ForexBot/src/"
    echo ""
fi
