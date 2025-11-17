"""
Pre-deployment check - Run this before deploying to VPS
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

print("="*60)
print("PRE-DEPLOYMENT CHECK")
print("="*60)
print()

all_passed = True

# Check 1: Python syntax
print("1. Checking Python syntax...")
import py_compile
files_to_check = [
    'src/ibkr/connector.py',
    'src/risk_management/emergency_stop.py',
    'src/risk_management/risk_manager.py',
    'src/bot.py',
    'main.py'
]

for file in files_to_check:
    try:
        py_compile.compile(file, doraise=True)
        print(f"   ✅ {file}")
    except Exception as e:
        print(f"   ❌ {file}: {e}")
        all_passed = False

print()

# Check 2: Import all modules
print("2. Checking imports...")
try:
    from src.ibkr.connector import IBKRConnector
    print("   ✅ IBKRConnector")
except Exception as e:
    print(f"   ❌ IBKRConnector: {e}")
    all_passed = False

try:
    from src.risk_management.emergency_stop import EmergencyStopSystem
    print("   ✅ EmergencyStopSystem")
except Exception as e:
    print(f"   ❌ EmergencyStopSystem: {e}")
    all_passed = False

try:
    from src.risk_management.risk_manager import RiskManager
    print("   ✅ RiskManager")
except Exception as e:
    print(f"   ❌ RiskManager: {e}")
    all_passed = False

try:
    from src.bot import EURCADTradingBot
    print("   ✅ EURCADTradingBot")
except Exception as e:
    print(f"   ❌ EURCADTradingBot: {e}")
    all_passed = False

print()

# Check 3: Verify new methods exist
print("3. Checking new reconnection methods...")
try:
    connector = IBKRConnector()

    assert hasattr(connector, 'check_connection'), "Missing check_connection"
    print("   ✅ check_connection() method exists")

    assert hasattr(connector, 'reconnect'), "Missing reconnect"
    print("   ✅ reconnect() method exists")

    assert hasattr(connector, 'ensure_connection'), "Missing ensure_connection"
    print("   ✅ ensure_connection() method exists")

    assert hasattr(connector, 'reconnect_attempts'), "Missing reconnect_attempts"
    print("   ✅ reconnect_attempts attribute exists")

    assert hasattr(connector, 'max_reconnect_attempts'), "Missing max_reconnect_attempts"
    print("   ✅ max_reconnect_attempts attribute exists")

except Exception as e:
    print(f"   ❌ Method check failed: {e}")
    all_passed = False

print()

# Check 4: Verify error tracking
print("4. Checking error tracking improvements...")
try:
    rm = RiskManager(10000)
    es = EmergencyStopSystem(rm)

    assert hasattr(es, 'consecutive_api_errors'), "Missing consecutive_api_errors"
    print("   ✅ consecutive_api_errors attribute exists")

    assert hasattr(es, 'max_consecutive_errors'), "Missing max_consecutive_errors"
    print("   ✅ max_consecutive_errors attribute exists")

    assert hasattr(es, 'error_reset_threshold'), "Missing error_reset_threshold"
    print("   ✅ error_reset_threshold attribute exists")

    # Test error tracking logic
    es.log_api_error()
    assert es.consecutive_api_errors == 1, "consecutive not incremented"
    assert es.api_error_count == 1, "total not incremented"
    print("   ✅ log_api_error() works correctly")

    es.reset_api_errors()
    assert es.consecutive_api_errors == 0, "consecutive not reset"
    assert es.api_error_count == 1, "total incorrectly reset"
    print("   ✅ reset_api_errors() works correctly")

except Exception as e:
    print(f"   ❌ Error tracking check failed: {e}")
    all_passed = False

print()

# Check 5: Configuration
print("5. Checking configuration...")
try:
    from config import config
    print(f"   ✅ Initial capital: ${config.INITIAL_CAPITAL:,.2f}")
    print(f"   ✅ Paper trading: {config.PAPER_TRADING}")
    print(f"   ✅ IBKR host: {config.IBKR_HOST}")
    print(f"   ✅ IBKR port: {config.IBKR_PAPER_PORT if config.PAPER_TRADING else config.IBKR_LIVE_PORT}")
except Exception as e:
    print(f"   ❌ Config check failed: {e}")
    all_passed = False

print()
print("="*60)
if all_passed:
    print("✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Commit changes: git add . && git commit -m 'Add reconnection logic'")
    print("2. Push to VPS: git push origin main")
    print("3. SSH to VPS and pull changes")
    print("4. Restart bot: pkill -f 'python.*main.py' && sleep 5 && nohup python3 main.py > bot_output.log 2>&1 &")
    print()
else:
    print("❌ SOME CHECKS FAILED - DO NOT DEPLOY")
    print("="*60)
    print()
    sys.exit(1)
