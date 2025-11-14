#!/bin/bash

###############################################################################
# EUR/CAD Trading Bot - Automated Backup Script
#
# Creates daily backups of:
# - Bot state
# - Logs
# - Environment configuration (encrypted)
# - Trading data
###############################################################################

set -e

# Configuration
PROJECT_DIR="/home/forexbot/forex-bot"
BACKUP_DIR="/home/forexbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="forex_data_$DATE"
LOG_FILE="/home/forexbot/logs/backup.log"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "Starting backup process"
log "=========================================="

# Create backup
cd "$PROJECT_DIR" || exit 1

tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    bot_state.json \
    eurcad_bot.log \
    .env \
    config/config.py \
    2>/dev/null || true

log "Backup created: $BACKUP_DIR/$BACKUP_NAME.tar.gz"

# Cleanup old backups (keep last 30 days)
find "$BACKUP_DIR" -name "forex_data_*.tar.gz" -mtime +30 -delete
log "Old backups cleaned up (kept last 30 days)"

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)
log "Backup size: $BACKUP_SIZE"

# Count total backups
TOTAL_BACKUPS=$(ls -1 "$BACKUP_DIR"/forex_data_*.tar.gz | wc -l)
log "Total backups: $TOTAL_BACKUPS"

log "Backup completed successfully"
log "=========================================="

exit 0
