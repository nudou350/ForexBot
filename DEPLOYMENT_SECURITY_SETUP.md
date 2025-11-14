# Deployment Security Setup Guide

This guide explains how to configure your VPS to work securely with the GitHub Actions deployment automation.

## Prerequisites

Your VPS must have the following security measures in place:
- ✅ SSH key-only authentication (no passwords)
- ✅ UFW firewall active (ports 22, 80, 443 only)
- ✅ fail2ban active and configured
- ✅ Applications bound to localhost only (127.0.0.1)
- ✅ Only `deploy` user allowed SSH access

## Step 1: Configure Passwordless Sudo for Deployment

The deployment automation requires the `deploy` user to manage systemd services without a password prompt.

**On your VPS, run:**

```bash
# Upload the sudoers configuration
scp scripts/sudoers-deploy deploy@72.60.56.80:/tmp/

# SSH into your VPS
ssh deploy@72.60.56.80

# Install the sudoers configuration
echo 'your-password' | sudo -S cp /tmp/sudoers-deploy /etc/sudoers.d/deploy-automation
echo 'your-password' | sudo -S chmod 440 /etc/sudoers.d/deploy-automation
echo 'your-password' | sudo -S chown root:root /etc/sudoers.d/deploy-automation

# Verify the syntax is correct
sudo visudo -c

# Test passwordless sudo
sudo systemctl status forexbot-trading  # Should not prompt for password
```

If you see any syntax errors, **DO NOT PROCEED**. Fix the errors first.

## Step 2: Create Project Directory Structure

```bash
# Create project directory
mkdir -p /home/deploy/forex-bot
mkdir -p /home/deploy/logs
mkdir -p /home/deploy/backups

# Initialize git repository
cd /home/deploy/forex-bot
git init
git remote add origin <your-github-repo-url>
git pull origin main

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 3: Create Systemd Service

Create `/etc/systemd/system/forexbot-trading.service`:

```ini
[Unit]
Description=EUR/CAD Forex Trading Bot
After=network.target

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/home/deploy/forex-bot
Environment="PATH=/home/deploy/forex-bot/venv/bin"
ExecStart=/home/deploy/forex-bot/venv/bin/python main.py

# Security hardening
PrivateTmp=yes
NoNewPrivileges=yes

# Restart policy
Restart=on-failure
RestartSec=10

# Logging
StandardOutput=append:/home/deploy/logs/bot-stdout.log
StandardError=append:/home/deploy/logs/bot-stderr.log

[Install]
WantedBy=multi-user.target
```

**Install and enable the service:**

```bash
sudo cp forexbot-trading.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable forexbot-trading
sudo systemctl start forexbot-trading
sudo systemctl status forexbot-trading
```

## Step 4: Configure GitHub Secrets

In your GitHub repository, go to **Settings → Secrets and variables → Actions** and add:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `VPS_SSH_KEY` | `<your-private-ssh-key>` | The SSH private key that matches the public key in `~/.ssh/authorized_keys` |

**That's it!** Only one secret is required. The VPS connection details (host, port, user) are hardcoded in the workflow for simplicity:
- Host: `72.60.56.80`
- Port: `22`
- User: `deploy` (enforced by VPS security hardening)

### Getting Your SSH Private Key

If you don't have the SSH private key that corresponds to the public key on the VPS:

```bash
# On your local machine, display your private key
cat ~/.ssh/id_ed25519  # or ~/.ssh/id_rsa

# Copy the entire output (including BEGIN and END lines)
# Paste it into the VPS_SSH_KEY secret
```

## Step 5: Test Deployment

### Manual Test (Recommended First)

Before relying on GitHub Actions, test the deployment manually:

```bash
# SSH into your VPS
ssh deploy@72.60.56.80

# Navigate to project directory
cd /home/deploy/forex-bot

# Run the deployment script
bash scripts/deploy.sh
```

If this works successfully, GitHub Actions deployment should work too.

### Trigger GitHub Actions Deployment

1. **Automatic:** Push to the `main` branch
   ```bash
   git add .
   git commit -m "Test deployment"
   git push origin main
   ```

2. **Manual:** Go to **Actions → Deploy to VPS → Run workflow**

## Step 6: Verify Deployment

After deployment completes, verify:

```bash
# Check service status
sudo systemctl status forexbot-trading

# Check bot process
ps aux | grep python.*main.py

# Check logs
tail -f /home/deploy/logs/bot-stdout.log

# Security compliance check
ss -tlnp | grep -E ':(3000|3001|3002|5000|8000)'
# Should show NO output or only 127.0.0.1 addresses (NOT 0.0.0.0)
```

## Security Features in Deployment

The deployment automation includes these security checks:

### 1. Firewall Verification
- Verifies UFW is active before deployment
- Deployment fails if firewall is disabled

### 2. Intrusion Prevention Verification
- Checks fail2ban is running
- Deployment fails if fail2ban is inactive

### 3. Localhost Binding Verification
- **CRITICAL:** Verifies no applications are bound to `0.0.0.0` (internet-accessible)
- Checks ports 3000, 3001, 3002, 5000, 8000
- Deployment fails if any application is exposed to the internet
- Applications MUST bind to `127.0.0.1` only

### 4. Deployment Logging
- All deployments logged to `~/deployment.log`
- Includes timestamps and exit codes
- Auditd also captures all deployment activity

### 5. Automatic Rollback
- If deployment fails, automatically rolls back to previous commit
- Reinstalls previous dependencies
- Restarts service with old code

## Troubleshooting

### "Permission denied" when running sudo commands

**Problem:** The sudoers configuration is not installed correctly.

**Solution:**
```bash
# Verify sudoers file exists
ls -l /etc/sudoers.d/deploy-automation

# Verify permissions
# Should be: -r--r----- root root
sudo chmod 440 /etc/sudoers.d/deploy-automation

# Test syntax
sudo visudo -c
```

### "Host key verification failed"

**Problem:** SSH host key not recognized by GitHub Actions runner.

**Solution:** The workflow includes `ssh-keyscan` to automatically add the host key. If this fails, check that `VPS_HOST` secret is correct.

### "Deployment script must be run as 'deploy' user"

**Problem:** `VPS_USER` secret is not set to `deploy`.

**Solution:**
1. Go to GitHub repo → Settings → Secrets
2. Update `VPS_USER` to exactly: `deploy`
3. Re-run the workflow

### "Application exposed to internet" error

**Problem:** Your application is binding to `0.0.0.0` instead of `127.0.0.1`.

**Solution:**
```python
# BAD - Exposes to internet
app.run(host='0.0.0.0', port=5000)

# GOOD - Localhost only
app.run(host='127.0.0.1', port=5000)
```

Then redeploy.

### Service fails to start after deployment

**Problem:** Application error, missing dependencies, or configuration issue.

**Solution:**
```bash
# Check service logs
sudo journalctl -u forexbot-trading -n 50

# Check application logs
tail -f /home/deploy/logs/bot-stdout.log
tail -f /home/deploy/logs/bot-stderr.log

# Check if virtual environment is activated
source /home/deploy/forex-bot/venv/bin/activate
python --version
pip list
```

## Security Best Practices

1. **Never disable security features during deployment**
   - Don't stop UFW
   - Don't stop fail2ban
   - Don't bind to 0.0.0.0

2. **Rotate SSH keys regularly**
   - Generate new SSH key pair every 90 days
   - Update `VPS_SSH_KEY` secret
   - Remove old public key from `~/.ssh/authorized_keys`

3. **Monitor deployment logs**
   - Review `~/deployment.log` weekly
   - Check auditd logs: `sudo ausearch -k sshd`

4. **Keep backups**
   - Deployment script automatically creates backups
   - Stored in `/home/deploy/backups/`
   - Keeps last 10 backups
   - Manually backup critical data separately

5. **Test in staging first**
   - If possible, test deployments on a staging VPS first
   - Verify security compliance before deploying to production

## VPS Security Documentation

For complete VPS security details, see:
- `VPS_SECURITY.md` - Comprehensive security documentation
- `VPS_DEPLOYMENT.md` - Deployment architecture guide

## Support

If you encounter issues:
1. Check GitHub Actions logs
2. Check deployment logs: `cat ~/deployment.log`
3. Check system logs: `sudo journalctl -xe`
4. Verify security configuration: `~/VPS_SECURITY.md`
