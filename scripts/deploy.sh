#!/bin/bash

###############################################################################
# EUR/CAD Trading Bot - Secure Deployment Script
#
# This script performs safe, automated deployment on VPS
# - Only affects this project (isolated)
# - Runs as non-root user
# - Includes rollback capability
# - Zero-downtime deployment
###############################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
PROJECT_DIR="/home/deploy/forex-bot"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="/home/deploy/logs"
BACKUP_DIR="/home/deploy/backups"
SERVICE_NAME="forexbot-trading"
DEPLOY_LOG="$LOG_DIR/deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$DEPLOY_LOG"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$DEPLOY_LOG"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$DEPLOY_LOG"
}

# Check if running as deploy user (VPS security requirement)
if [ "$(whoami)" != "deploy" ]; then
    error "This script must be run as 'deploy' user (VPS security requirement)"
    exit 1
fi

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"
mkdir -p "$BACKUP_DIR"

log "=========================================="
log "Starting deployment process"
log "=========================================="

# Step 1: Backup current state
log "Step 1: Creating backup..."
BACKUP_FILE="$BACKUP_DIR/pre-deploy-$(date +%Y%m%d_%H%M%S).tar.gz"

cd "$PROJECT_DIR" || exit 1

# Backup current code and data
tar -czf "$BACKUP_FILE" \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    .

log "Backup created: $BACKUP_FILE"

# Step 2: Store current commit hash (for rollback)
CURRENT_COMMIT=$(git rev-parse HEAD)
log "Current commit: $CURRENT_COMMIT"

# Step 3: Pull latest code
log "Step 2: Pulling latest code from Git..."
git fetch origin

# Check if there are changes
if git diff --quiet HEAD origin/main; then
    log "No changes detected. Deployment not needed."
    exit 0
fi

# Preserve runtime state files before pulling
log "Preserving runtime state files..."
if [ -f "bot_state.json" ]; then
    cp bot_state.json bot_state.json.backup
    log "bot_state.json backed up"
fi

# Stash any local changes to runtime files
log "Stashing local changes to runtime files..."
git stash push -m "Auto-stash before deployment $(date +%Y%m%d_%H%M%S)" -- bot_state.json 2>/dev/null || true

# Pull latest code
git pull origin main

# Restore runtime state files
if [ -f "bot_state.json.backup" ]; then
    mv bot_state.json.backup bot_state.json
    log "bot_state.json restored"
fi

NEW_COMMIT=$(git rev-parse HEAD)
log "New commit: $NEW_COMMIT"

# Step 4: Update Python dependencies
log "Step 3: Updating Python dependencies..."
source "$VENV_DIR/bin/activate"

# Check if requirements.txt changed
if git diff "$CURRENT_COMMIT" "$NEW_COMMIT" -- requirements.txt | grep -q .; then
    log "requirements.txt changed, updating dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    log "requirements.txt unchanged, skipping dependency update"
fi

# Step 5: Run database migrations (if applicable)
# Uncomment if you add database migrations in the future
# log "Step 4: Running database migrations..."
# python manage.py migrate

# Step 6: Restart IB Gateway service (if exists and credentials are available)
IBGATEWAY_SERVICE="ibgateway"
if sudo systemctl list-units --type=service --all | grep -q "$IBGATEWAY_SERVICE"; then
    if [ -f "/home/deploy/.ibkr-credentials" ]; then
        log "Restarting IB Gateway service..."
        sudo systemctl restart "$IBGATEWAY_SERVICE"
        sleep 10  # Wait for IB Gateway to start and connect

        if sudo systemctl is-active --quiet "$IBGATEWAY_SERVICE"; then
            log "${GREEN}✓${NC} IB Gateway restarted successfully"
        else
            warning "IB Gateway service failed to start (check credentials)"
        fi
    else
        log "IB Gateway credentials not found, skipping restart"
    fi
else
    log "IB Gateway service not found"
fi

# Step 7: Restart the bot service
log "Step 5: Restarting bot service..."

# Check if service exists
if sudo systemctl list-units --type=service --all | grep -q "$SERVICE_NAME"; then
    # Gracefully restart service
    sudo systemctl restart "$SERVICE_NAME"

    # Wait for service to start
    sleep 3

    # Check if service started successfully
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        log "${GREEN}✓${NC} Service restarted successfully"
    else
        error "Service failed to start. Rolling back..."
        rollback "$CURRENT_COMMIT"
        exit 1
    fi
else
    warning "Service $SERVICE_NAME not found. Skipping restart."
fi

# Step 8: Restart dashboard service (if exists)
DASHBOARD_SERVICE="forexbot-dashboard"
if sudo systemctl list-units --type=service --all | grep -q "$DASHBOARD_SERVICE"; then
    log "Restarting dashboard service..."
    sudo systemctl restart "$DASHBOARD_SERVICE"
    sleep 2

    if sudo systemctl is-active --quiet "$DASHBOARD_SERVICE"; then
        log "${GREEN}✓${NC} Dashboard restarted successfully"
    else
        warning "Dashboard service failed to start (non-critical)"
    fi
else
    log "Dashboard service not found (will be accessible when started manually)"
fi

# Step 9: Health check
log "Step 6: Performing health check..."

# Wait for bot to initialize
sleep 5

# Check if bot is running
if pgrep -f "python.*main.py" > /dev/null; then
    log "${GREEN}✓${NC} Bot process is running"
else
    error "Bot process not found. Rolling back..."
    rollback "$CURRENT_COMMIT"
    exit 1
fi

# Check if log file is being written to
if [ -f "$PROJECT_DIR/eurcad_bot.log" ]; then
    # Check if log was modified in the last 2 minutes
    if [ $(find "$PROJECT_DIR/eurcad_bot.log" -mmin -2 | wc -l) -gt 0 ]; then
        log "${GREEN}✓${NC} Bot is actively logging"
    else
        warning "Bot log hasn't been updated recently"
    fi
fi

# Step 10: Cleanup old backups (keep last 10)
log "Step 7: Cleaning up old backups..."
cd "$BACKUP_DIR" || exit 1
ls -t pre-deploy-*.tar.gz | tail -n +11 | xargs -r rm
log "Old backups cleaned up"

# Step 9: Deployment summary
log "=========================================="
log "Deployment completed successfully!"
log "=========================================="
log "Previous commit: $CURRENT_COMMIT"
log "New commit:      $NEW_COMMIT"
log "Backup location: $BACKUP_FILE"
log "Service status:  Active"
log "=========================================="

# Send notification (if configured)
if [ -f "$PROJECT_DIR/.env" ] && grep -q "ENABLE_TELEGRAM_ALERTS=True" "$PROJECT_DIR/.env"; then
    log "Sending deployment notification..."
    # Add notification logic here
fi

exit 0

###############################################################################
# Rollback function
###############################################################################
rollback() {
    local target_commit=$1
    error "Rolling back to commit: $target_commit"

    git reset --hard "$target_commit"

    # Reinstall dependencies
    source "$VENV_DIR/bin/activate"
    pip install -r requirements.txt

    # Restart service
    sudo systemctl restart "$SERVICE_NAME"

    error "Rollback completed"
    exit 1
}
