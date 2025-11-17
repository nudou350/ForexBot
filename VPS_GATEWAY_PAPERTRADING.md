# VPS IB Gateway Paper Trading Setup

This document explains the complete setup for running the EUR/CAD ForexBot on a VPS with Interactive Brokers Gateway (IB Gateway) for paper trading.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
- [How It Works](#how-it-works)
- [Deployment](#deployment)
- [Managing Services](#managing-services)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

---

## Overview

The ForexBot runs on VPS `72.60.56.80` and connects to Interactive Brokers via IB Gateway for paper trading on EUR/CAD. The entire system is automated and will restart on VPS reboot.

**Key Information:**
- VPS IP: `72.60.56.80`
- Trading Mode: **Paper Trading Only**
- Currency Pair: EUR/CAD
- Dashboard URL: http://72.60.56.80/forex-dashboard
- Initial Capital: $1,000 (paper money)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        VPS (72.60.56.80)                    │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │  IB Gateway  │◄────────┤  ForexBot    │                │
│  │  (headless)  │ Port    │  Service     │                │
│  │              │ 7497    │              │                │
│  └──────┬───────┘         └──────┬───────┘                │
│         │                         │                         │
│  ┌──────▼───────┐         ┌──────▼───────┐                │
│  │   Xvfb :1    │         │  Dashboard   │                │
│  │  (virtual    │         │  Service     │                │
│  │   display)   │         │  Port 8050   │                │
│  └──────────────┘         └──────┬───────┘                │
│                                   │                         │
│                            ┌──────▼───────┐                │
│                            │    Nginx     │                │
│                            │  Reverse     │                │
│                            │   Proxy      │                │
│                            └──────┬───────┘                │
└────────────────────────────────────┼──────────────────────┘
                                     │
                         ┌───────────▼──────────┐
                         │  Internet (Port 80)  │
                         │  /forex-dashboard    │
                         └──────────────────────┘
```

---

## Components

### 1. IB Gateway (Interactive Brokers Gateway)

**What it is:** Headless version of TWS (Trader Workstation) that provides API access for automated trading.

**Purpose:**
- Connects to Interactive Brokers servers
- Provides API on port 7497 for paper trading
- Handles authentication and market data

**Installation Location:** `/home/deploy/IBGateway/`

**Service:** `ibgateway.service`

**How it runs:**
- Runs in headless mode using Xvfb (virtual display)
- Auto-starts on VPS boot
- Auto-restarts on failure (30s delay)
- Managed by systemd

**Configuration:**
- Credentials stored in: `/home/deploy/.ibkr-credentials`
- Trading mode: Paper Trading (port 7497)
- Trusted IPs: 127.0.0.1 only
- API enabled for localhost connections

---

### 2. Xvfb (X Virtual Framebuffer)

**What it is:** Virtual display server that allows GUI applications to run without a physical display.

**Purpose:** IB Gateway is a GUI application and needs a display to run. Xvfb provides a virtual display `:1`.

**How it works:**
- Creates virtual display `:1` at 1024x768x24
- IB Gateway renders to this virtual display
- No physical monitor needed

---

### 3. ForexBot Trading Service

**What it is:** Your EUR/CAD trading bot written in Python.

**Location:** `/home/deploy/forex-bot/`

**Service:** `forexbot-trading.service`

**How it works:**
1. Connects to IB Gateway API on port 7497
2. Fetches real-time EUR/CAD market data
3. Analyzes market using multiple strategies
4. Places trades based on signals
5. Manages risk and positions
6. Logs all activity

**Python Environment:**
- Virtual environment: `/home/deploy/forex-bot/venv/`
- Requirements installed from `requirements.txt`
- Main entry point: `main.py`

**Logs:**
- stdout: `/home/deploy/logs/bot-stdout.log`
- stderr: `/home/deploy/logs/bot-stderr.log`

---

### 4. Dashboard Service

**What it is:** Real-time web dashboard for monitoring the bot's performance.

**Location:** `/home/deploy/forex-bot/`

**Service:** `forexbot-dashboard.service`

**Technology:** Plotly Dash (Python web framework)

**Internal Port:** 8050 (localhost only)

**External Access:** http://72.60.56.80/forex-dashboard (via Nginx)

**Features:**
- Real-time EUR/CAD price charts
- Open positions display
- Trade history
- Performance metrics
- Account balance tracking

---

### 5. Nginx Reverse Proxy

**What it is:** Web server that routes external requests to internal services.

**Configuration:** `/etc/nginx/sites-available/cryptobot`

**Routing:**
- `/` → CryptoBot (port 3001)
- `/forex-dashboard` → ForexBot Dashboard (port 8050)

**Security:**
- Rate limiting enabled
- Security headers applied
- Only HTTP (port 80) exposed

---

### 6. VNC Server (x11vnc)

**What it is:** VNC server for remote desktop access to the virtual display.

**Purpose:** Allows you to view and interact with IB Gateway GUI remotely.

**When needed:**
- Initial IB Gateway login and API configuration
- Troubleshooting login issues
- Changing IB Gateway settings

**How to connect:**
1. Create SSH tunnel: `ssh -L 5900:localhost:5900 deploy@72.60.56.80`
2. Open VNC client: `localhost:5900`
3. Password: `forexbot2024`

---

## How It Works

### System Startup Sequence

1. **VPS Boots**
2. **systemd starts enabled services:**
   - `ibgateway.service` starts
   - Xvfb creates virtual display `:1`
   - IB Gateway launches and connects to IB servers
   - API becomes available on port 7497
3. **ForexBot services start:**
   - `forexbot-trading.service` starts
   - Connects to IB Gateway API
   - Begins market analysis
   - `forexbot-dashboard.service` starts
   - Dashboard becomes available
4. **Nginx routes traffic:**
   - External requests to `/forex-dashboard` proxied to dashboard

---

### Data Flow for a Trade

```
1. IB Servers → IB Gateway (market data)
2. IB Gateway → ForexBot (via API port 7497)
3. ForexBot → Analyzes data with strategies
4. ForexBot → Generates signal
5. ForexBot → Places order via IB Gateway API
6. IB Gateway → Sends order to IB Servers
7. IB Servers → Confirms execution
8. IB Gateway → ForexBot (confirmation)
9. ForexBot → Updates dashboard
10. Dashboard → User's browser
```

---

## Deployment

### Automatic Deployment via GitHub Actions

When you push to the `main` branch, GitHub Actions automatically deploys to the VPS.

**Workflow:** `.github/workflows/deploy.yml`

**Steps performed:**
1. Checkout code
2. Setup SSH with key from `VPS_SSH_KEY` secret
3. Deploy IBKR credentials from secrets
4. Connect to VPS and run deployment script
5. Security compliance verification
6. Service health checks

**GitHub Secrets Required:**
- `VPS_SSH_KEY` - SSH private key for deploy user
- `IBKR_USERNAME` - IBKR username (raphapereira)
- `IBKR_PASSWORD` - IBKR password (Y2xE#JhDeJb0k4)

**Deployment Script:** `scripts/deploy.sh`

### Manual Deployment

If you need to deploy manually:

```bash
# SSH into VPS
ssh deploy@72.60.56.80

# Navigate to project
cd /home/deploy/forex-bot

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies (if requirements.txt changed)
pip install -r requirements.txt

# Restart services
sudo systemctl restart ibgateway
sleep 10
sudo systemctl restart forexbot-trading
sudo systemctl restart forexbot-dashboard

# Check status
sudo systemctl status forexbot-trading
```

---

## Managing Services

### Service Management Commands

All services use systemd. You must use `sudo` for service commands.

**Check service status:**
```bash
sudo systemctl status ibgateway
sudo systemctl status forexbot-trading
sudo systemctl status forexbot-dashboard
```

**Start services:**
```bash
sudo systemctl start ibgateway
sudo systemctl start forexbot-trading
sudo systemctl start forexbot-dashboard
```

**Stop services:**
```bash
sudo systemctl stop ibgateway
sudo systemctl stop forexbot-trading
sudo systemctl stop forexbot-dashboard
```

**Restart services:**
```bash
sudo systemctl restart ibgateway
sudo systemctl restart forexbot-trading
sudo systemctl restart forexbot-dashboard
```

**Enable auto-start on boot:**
```bash
sudo systemctl enable ibgateway
sudo systemctl enable forexbot-trading
sudo systemctl enable forexbot-dashboard
```

**Disable auto-start:**
```bash
sudo systemctl disable ibgateway
```

---

### Service Dependencies

**IMPORTANT:** Services must start in this order:

1. **ibgateway** (must be first)
2. **forexbot-trading** (waits for IB Gateway API)
3. **forexbot-dashboard** (independent)

If you restart IB Gateway, you must also restart forexbot-trading:

```bash
sudo systemctl restart ibgateway
sleep 10  # Wait for IB Gateway API to be ready
sudo systemctl restart forexbot-trading
```

---

## Monitoring

### View Real-Time Logs

**Bot trading activity:**
```bash
ssh deploy@72.60.56.80 "tail -f /home/deploy/logs/bot-stdout.log"
```

**Bot errors:**
```bash
ssh deploy@72.60.56.80 "tail -f /home/deploy/logs/bot-stderr.log"
```

**IB Gateway logs:**
```bash
ssh deploy@72.60.56.80 "tail -f /home/deploy/logs/ibgateway-stdout.log"
```

**Dashboard logs:**
```bash
ssh deploy@72.60.56.80 "sudo journalctl -u forexbot-dashboard -f"
```

**All services at once:**
```bash
ssh deploy@72.60.56.80 "sudo journalctl -f -u ibgateway -u forexbot-trading -u forexbot-dashboard"
```

---

### Check System Health

**Verify all services are running:**
```bash
ssh deploy@72.60.56.80 "sudo systemctl is-active ibgateway forexbot-trading forexbot-dashboard"
```

**Check IB Gateway API is listening:**
```bash
ssh deploy@72.60.56.80 "ss -tlnp | grep 7497"
```
Should show: `LISTEN 0 50 *:7497 *:*`

**Check dashboard is accessible:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://72.60.56.80/forex-dashboard
```
Should return: `200`

**Check bot connection to IB Gateway:**
```bash
ssh deploy@72.60.56.80 "tail -20 /home/deploy/logs/bot-stdout.log | grep -i connected"
```
Should show: `Connected to IBKR on port 7497`

---

### Dashboard Monitoring

Open in browser: http://72.60.56.80/forex-dashboard

**What to check:**
- Current EUR/CAD price is updating
- Account balance shows $1,000 (or current value)
- No error messages displayed
- Charts are rendering

---

## Troubleshooting

### Problem: Bot shows "Not connected" errors

**Cause:** IB Gateway API is not running or not ready.

**Solution:**
```bash
# Check if IB Gateway is running
ssh deploy@72.60.56.80 "sudo systemctl status ibgateway"

# Check if API port is listening
ssh deploy@72.60.56.80 "ss -tlnp | grep 7497"

# If not running, restart IB Gateway
ssh deploy@72.60.56.80 "sudo systemctl restart ibgateway"

# Wait 10 seconds, then restart bot
sleep 10
ssh deploy@72.60.56.80 "sudo systemctl restart forexbot-trading"
```

---

### Problem: IB Gateway service keeps restarting

**Cause:** IB Gateway crashed, credentials invalid, or API misconfigured.

**Check logs:**
```bash
ssh deploy@72.60.56.80 "tail -50 /home/deploy/logs/ibgateway-stderr.log"
```

**Common issues:**
1. **Invalid credentials:** Check `/home/deploy/.ibkr-credentials`
2. **Display error:** Xvfb not running
3. **API not enabled:** Need to login via VNC and enable API

**Solution - Reconfigure via VNC:**
```bash
# On your local machine
ssh -L 5900:localhost:5900 deploy@72.60.56.80

# Open VNC viewer to localhost:5900
# Password: forexbot2024

# Login to IB Gateway
# Username: raphapereira
# Password: Y2xE#JhDeJb0k4

# Configure → Settings → API → Settings
# Ensure "Allow connections from localhost only" is checked
# Socket port: 7497
# Trusted IPs: 127.0.0.1
```

---

### Problem: Dashboard shows 404 error

**Cause:** Nginx not configured correctly or dashboard service not running.

**Solution:**
```bash
# Check if dashboard service is running
ssh deploy@72.60.56.80 "sudo systemctl status forexbot-dashboard"

# If not running, start it
ssh deploy@72.60.56.80 "sudo systemctl start forexbot-dashboard"

# Check if port 8050 is listening
ssh deploy@72.60.56.80 "ss -tlnp | grep 8050"

# Test nginx configuration
ssh deploy@72.60.56.80 "sudo nginx -t"

# Reload nginx if needed
ssh deploy@72.60.56.80 "sudo systemctl reload nginx"
```

---

### Problem: "Trading halted: Multiple API errors"

**Cause:** Bot accumulated too many errors while trying to connect before IB Gateway was ready.

**Solution:**
```bash
# Simply restart the bot to reset error counter
ssh deploy@72.60.56.80 "sudo systemctl restart forexbot-trading"

# Check logs to confirm it connected
ssh deploy@72.60.56.80 "tail -20 /home/deploy/logs/bot-stdout.log"
```

---

### Problem: VNC connection refused

**Cause:** VNC server not running or SSH tunnel not established.

**Solution:**
```bash
# Start VNC server on VPS
ssh deploy@72.60.56.80 "x11vnc -display :1 -rfbauth ~/.vnc/passwd -localhost -forever -bg -o /home/deploy/logs/vnc.log"

# Verify VNC is listening
ssh deploy@72.60.56.80 "ss -tlnp | grep 5900"

# Create SSH tunnel from your local machine
ssh -L 5900:localhost:5900 deploy@72.60.56.80

# Connect VNC viewer to localhost:5900
```

---

### Problem: After VPS reboot, services don't start

**Cause:** Services not enabled for auto-start.

**Solution:**
```bash
ssh deploy@72.60.56.80 "sudo systemctl enable ibgateway forexbot-trading forexbot-dashboard"
```

---

### Problem: Bot can't fetch historical data

**Cause:** Market is closed or IB Gateway doesn't have market data subscription.

**Check market hours:**
- Forex market is open 24/5 (Sunday 5 PM EST - Friday 5 PM EST)
- Data may be delayed or unavailable outside these hours

**Solution:**
- Wait for market to open
- Verify in IB Gateway that EUR/CAD is available for paper trading
- Check bot logs for specific error messages

---

## Security Considerations

### Credentials Management

**IBKR Credentials:**
- Stored in: `/home/deploy/.ibkr-credentials`
- Permissions: `600` (readable only by deploy user)
- Never committed to Git
- Deployed via GitHub Secrets

**SSH Access:**
- Only `deploy` user allowed
- Key-based authentication only (no passwords)
- SSH key stored in GitHub Secrets

---

### Network Security

**Firewall (UFW):**
- Only ports 22 (SSH), 80 (HTTP), 443 (HTTPS) open to internet
- All other ports blocked

**IB Gateway API:**
- Listens on `*:7497` but only accepts localhost connections
- Trusted IPs: 127.0.0.1 only
- Not exposed to internet

**Dashboard:**
- Internal port 8050 only accessible via localhost
- Exposed to internet via nginx reverse proxy
- No authentication (paper trading only - no sensitive data)

---

### Service Security

**systemd Security Hardening:**

All services run with:
- `PrivateTmp=yes` - Isolated /tmp directory
- `NoNewPrivileges=yes` - Cannot gain new privileges
- `User=deploy` - Non-root user
- `Group=deploy` - Non-root group

---

### Monitoring and Auditing

**Deployment Logging:**
- All deployments logged to: `/home/deploy/deployment.log`
- Includes timestamps and exit codes

**Service Logs:**
- Managed by systemd journal
- Accessible via `journalctl`

**Security Compliance Checks:**
- GitHub Actions verifies UFW is active
- Checks fail2ban is running
- Ensures no applications exposed to internet

---

## Advanced Configuration

### Changing Paper Trading to Live Trading

**⚠️ WARNING:** Only do this when you're ready for real money trading!

1. Login to IB Gateway via VNC
2. Change trading mode from "Paper Trading" to "Live Trading"
3. API will switch from port 7497 to 7496
4. Update bot configuration to use port 7496
5. Restart services

**NOT RECOMMENDED** until thoroughly tested in paper trading mode.

---

### Increasing Initial Capital (Paper Trading)

Your IBKR paper trading account has a default balance. To change it:

1. Login to IB Gateway via VNC
2. Configure → Settings → Paper Trading Account
3. Adjust balance as needed
4. Restart bot service

---

### Adding Email Alerts

The bot includes alert functionality. To enable:

1. Edit `/home/deploy/forex-bot/.env`
2. Add email configuration:
   ```
   ENABLE_EMAIL_ALERTS=True
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USER=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   ALERT_EMAIL=recipient@email.com
   ```
3. Restart bot: `sudo systemctl restart forexbot-trading`

---

### Viewing Trade History

**Via Dashboard:**
- Open http://72.60.56.80/forex-dashboard
- Trade history section shows all executed trades

**Via Logs:**
```bash
ssh deploy@72.60.56.80 "grep 'TRADE' /home/deploy/logs/bot-stdout.log"
```

**Via IB Gateway:**
- Connect via VNC
- IB Gateway shows all trades in the Activity panel

---

## Backup and Recovery

### Backup Strategy

**What to backup:**
1. Trading bot code: `/home/deploy/forex-bot/`
2. Credentials: `/home/deploy/.ibkr-credentials`
3. Logs: `/home/deploy/logs/`
4. Service files: `/etc/systemd/system/{ibgateway,forexbot-*}.service`

**Automatic Backups:**
- Deployment script creates backup before each deploy
- Location: `/home/deploy/backups/`
- Keeps last 10 backups
- Format: `pre-deploy-YYYYMMDD_HHMMSS.tar.gz`

**Manual Backup:**
```bash
ssh deploy@72.60.56.80 "cd /home/deploy && tar -czf backup-$(date +%Y%m%d).tar.gz forex-bot .ibkr-credentials logs"
scp deploy@72.60.56.80:/home/deploy/backup-*.tar.gz ./
```

---

### Disaster Recovery

**If VPS crashes or needs to be rebuilt:**

1. Setup new VPS with security hardening (see VPS_SECURITY.md)
2. Run GitHub Actions deployment
3. Services will auto-deploy
4. Login to IB Gateway via VNC and enable API
5. Verify all services are running

**If only bot service crashes:**
```bash
sudo systemctl restart forexbot-trading
```

**If IB Gateway credentials change:**
1. Update GitHub Secrets: `IBKR_USERNAME`, `IBKR_PASSWORD`
2. Run deployment or manually update `/home/deploy/.ibkr-credentials`
3. Restart IB Gateway: `sudo systemctl restart ibgateway`

---

## Performance Optimization

### Resource Usage

**Current resource allocation:**
- IB Gateway: ~250 MB RAM
- ForexBot: ~80 MB RAM
- Dashboard: ~60 MB RAM
- Xvfb: ~70 MB RAM
- **Total:** ~460 MB RAM (VPS has 8 GB - plenty of headroom)

**CPU Usage:**
- Typically < 5% during normal operation
- Spikes during market data analysis

**Disk Usage:**
- Bot code: ~50 MB
- IB Gateway: ~500 MB
- Logs grow over time (rotate if needed)

---

### Log Rotation

To prevent logs from consuming too much disk space:

```bash
# Check log sizes
ssh deploy@72.60.56.80 "du -sh /home/deploy/logs/*"

# Manually rotate logs
ssh deploy@72.60.56.80 "cd /home/deploy/logs && gzip bot-stdout.log && mv bot-stdout.log.gz bot-stdout-$(date +%Y%m%d).log.gz"

# Restart service to create new log
ssh deploy@72.60.56.80 "sudo systemctl restart forexbot-trading"
```

---

## Related Documentation

- `VPS_SECURITY.md` - Complete VPS security hardening guide
- `DEPLOYMENT_SECURITY_SETUP.md` - GitHub Actions deployment setup
- `README.md` - General project documentation

---

## Support and Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Check dashboard for any errors
- Review trade performance
- Verify all services are running

**Monthly:**
- Review logs for any warnings
- Check disk space usage
- Verify GitHub Actions deployments are working
- Rotate logs if needed

**As Needed:**
- IB Gateway updates (auto-updates enabled)
- Python dependency updates
- Security patches (via GitHub Actions)

---

## Quick Reference

### Essential URLs

- Dashboard: http://72.60.56.80/forex-dashboard
- CryptoBot: http://72.60.56.80/

### Essential Commands

```bash
# Check all services
ssh deploy@72.60.56.80 "sudo systemctl status ibgateway forexbot-trading forexbot-dashboard"

# View bot logs
ssh deploy@72.60.56.80 "tail -f /home/deploy/logs/bot-stdout.log"

# Restart bot
ssh deploy@72.60.56.80 "sudo systemctl restart forexbot-trading"

# Full system restart
ssh deploy@72.60.56.80 "sudo systemctl restart ibgateway && sleep 10 && sudo systemctl restart forexbot-trading forexbot-dashboard"
```

### Service Locations

- Bot code: `/home/deploy/forex-bot/`
- IB Gateway: `/home/deploy/IBGateway/`
- Logs: `/home/deploy/logs/`
- Credentials: `/home/deploy/.ibkr-credentials`
- Service files: `/etc/systemd/system/`

### Important Ports

- 7497: IB Gateway API (paper trading)
- 8050: Dashboard (internal)
- 80: HTTP (external access)
- 5900: VNC (localhost only)

---

**Last Updated:** 2025-11-14
**Version:** 1.0
**Maintainer:** ForexBot Team
