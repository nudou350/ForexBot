#!/bin/bash

###############################################################################
# Quick Fix Script - Run this ONCE on VPS to resolve bot_state.json conflict
# This will fix the current deployment issue and pull the updated deploy.sh
###############################################################################

set -e

PROJECT_DIR="/home/deploy/forex-bot"

echo "=========================================="
echo "Fixing deployment conflict..."
echo "=========================================="

cd "$PROJECT_DIR" || exit 1

# Backup bot_state.json if it exists
if [ -f "bot_state.json" ]; then
    echo "Backing up bot_state.json..."
    cp bot_state.json bot_state.json.backup
    echo "✓ bot_state.json backed up"
fi

# Stash the conflicting file
echo "Stashing local changes to bot_state.json..."
git stash push -m "Manual fix: stash bot_state.json $(date +%Y%m%d_%H%M%S)" -- bot_state.json 2>/dev/null || true

# Pull latest code (includes updated deploy.sh)
echo "Pulling latest code from GitHub..."
git fetch origin
git pull origin main

# Restore bot_state.json
if [ -f "bot_state.json.backup" ]; then
    echo "Restoring bot_state.json..."
    mv bot_state.json.backup bot_state.json
    echo "✓ bot_state.json restored"
fi

echo "=========================================="
echo "✓ Fix completed successfully!"
echo "=========================================="
echo "The deployment script has been updated."
echo "Future deployments will handle bot_state.json automatically."
echo "=========================================="

exit 0
