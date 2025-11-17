#!/bin/bash

###############################################################################
# EUR/CAD Trading Bot - Service Restart Script
#
# This script restarts the ForexBot service and checks status
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "Restarting ForexBot Services"
echo "=========================================="

# Check if IB Gateway is running
echo "Checking IB Gateway status..."
if sudo systemctl is-active --quiet ibgateway; then
    echo -e "${GREEN}✓${NC} IB Gateway is running"
else
    echo -e "${RED}✗${NC} IB Gateway is NOT running"
    echo "Attempting to start IB Gateway..."

    if sudo systemctl start ibgateway 2>/dev/null; then
        echo -e "${GREEN}✓${NC} IB Gateway started"
        sleep 15  # Wait for Gateway to connect
    else
        echo -e "${YELLOW}⚠${NC}  IB Gateway service not found or failed to start"
        echo "The bot requires IB Gateway to connect to Interactive Brokers"
        echo "Please set up IB Gateway first. See VPS_GATEWAY_PAPERTRADING.md"
    fi
fi

# Restart ForexBot trading service
echo ""
echo "Restarting ForexBot trading service..."
if sudo systemctl restart forexbot-trading 2>/dev/null; then
    echo -e "${GREEN}✓${NC} ForexBot trading service restarted"
else
    echo -e "${RED}✗${NC} ForexBot trading service not found"
    echo "Service may not be installed yet"
fi

# Restart dashboard (optional)
echo ""
echo "Restarting ForexBot dashboard..."
if sudo systemctl restart forexbot-dashboard 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Dashboard restarted"
else
    echo -e "${YELLOW}⚠${NC}  Dashboard service not found (optional)"
fi

# Wait for services to initialize
echo ""
echo "Waiting for services to initialize..."
sleep 5

# Check status
echo ""
echo "=========================================="
echo "Service Status"
echo "=========================================="

if sudo systemctl is-active --quiet ibgateway; then
    echo -e "${GREEN}✓${NC} IB Gateway: Running"
else
    echo -e "${RED}✗${NC} IB Gateway: Not running"
fi

if sudo systemctl is-active --quiet forexbot-trading; then
    echo -e "${GREEN}✓${NC} ForexBot Trading: Running"
else
    echo -e "${RED}✗${NC} ForexBot Trading: Not running"
fi

if sudo systemctl is-active --quiet forexbot-dashboard; then
    echo -e "${GREEN}✓${NC} Dashboard: Running"
else
    echo -e "${YELLOW}⚠${NC}  Dashboard: Not running"
fi

# Show recent logs
echo ""
echo "=========================================="
echo "Recent Bot Logs (last 20 lines)"
echo "=========================================="
if sudo journalctl -u forexbot-trading -n 20 --no-pager 2>/dev/null; then
    :
else
    echo "Could not retrieve logs"
fi

echo ""
echo "=========================================="
echo "Restart complete!"
echo "=========================================="
