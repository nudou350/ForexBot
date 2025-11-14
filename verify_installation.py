"""
Installation Verification Script
Run this to verify the EUR/CAD Trading Bot is properly installed
"""

import sys
import os
import asyncio

# Fix for Python 3.14 event loop compatibility
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(text)
    print("="*70)

def print_check(name, status, details=""):
    """Print check result"""
    symbol = "[PASS]" if status else "[FAIL]"
    print(f"{symbol} {name}")
    if details:
        print(f"  {details}")

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    is_valid = version.major == 3 and version.minor >= 8
    details = f"Python {version.major}.{version.minor}.{version.micro}"
    return is_valid, details

def check_dependencies():
    """Check required packages"""
    required = {
        'ib_insync': '0.9.86',
        'pandas': '2.1.4',
        'numpy': '1.26.2'
    }

    results = {}
    for package, expected_version in required.items():
        try:
            module = __import__(package.replace('-', '_'))
            version = getattr(module, '__version__', 'unknown')
            results[package] = (True, version)
        except ImportError:
            results[package] = (False, 'not installed')

    return results

def check_project_structure():
    """Check project files exist"""
    required_files = [
        'main.py',
        'config/config.py',
        'src/bot.py',
        'src/strategies/mean_reversion.py',
        'src/strategies/trend_following.py',
        'src/strategies/grid_trading.py',
        'src/risk_management/risk_manager.py',
        'src/risk_management/emergency_stop.py',
        'src/market_analysis/regime_detector.py',
        'src/ibkr/connector.py',
        'src/backtesting/backtester.py'
    ]

    results = {}
    for file_path in required_files:
        exists = os.path.exists(file_path)
        results[file_path] = exists

    return results

def check_imports():
    """Check if modules can be imported"""
    modules = [
        'src.strategies.mean_reversion',
        'src.strategies.trend_following',
        'src.strategies.grid_trading',
        'src.risk_management.risk_manager',
        'src.risk_management.emergency_stop',
        'src.market_analysis.regime_detector',
        'src.ibkr.connector',
        'src.backtesting.backtester',
        'config.config'
    ]

    results = {}
    for module_name in modules:
        try:
            __import__(module_name)
            results[module_name] = True
        except Exception as e:
            results[module_name] = (False, str(e))

    return results

def main():
    """Run all verification checks"""
    print_header("EUR/CAD Trading Bot - Installation Verification")

    all_passed = True

    # Check Python version
    print_header("1. Python Version Check")
    is_valid, details = check_python_version()
    print_check("Python Version (>=3.8)", is_valid, details)
    all_passed = all_passed and is_valid

    # Check dependencies
    print_header("2. Dependencies Check")
    deps = check_dependencies()
    for package, (installed, version) in deps.items():
        print_check(f"{package}", installed, f"Version: {version}")
        all_passed = all_passed and installed

    # Check project structure
    print_header("3. Project Structure Check")
    files = check_project_structure()
    missing = [f for f, exists in files.items() if not exists]
    if missing:
        for file_path in missing:
            print_check(file_path, False)
        all_passed = False
    else:
        print_check("All required files present", True, f"{len(files)} files found")

    # Check imports
    print_header("4. Module Import Check")
    imports = check_imports()
    for module, result in imports.items():
        if result is True:
            print_check(module, True)
        else:
            print_check(module, False, result[1] if isinstance(result, tuple) else "")
            all_passed = False

    # Configuration check
    print_header("5. Configuration Check")
    try:
        from config import config
        print_check("Config loaded", True)
        print(f"  Paper Trading: {config.PAPER_TRADING}")
        print(f"  Initial Capital: ${config.INITIAL_CAPITAL:,}")
        print(f"  Risk per Trade: {config.MAX_RISK_PER_TRADE*100}%")
    except Exception as e:
        print_check("Config loaded", False, str(e))
        all_passed = False

    # Final result
    print_header("VERIFICATION RESULT")
    if all_passed:
        print("\n[SUCCESS] ALL CHECKS PASSED!")
        print("\nYour EUR/CAD Trading Bot is properly installed.")
        print("\nNext steps:")
        print("1. Configure IBKR TWS/Gateway (port 7497 for paper trading)")
        print("2. Run tests: python tests/test_strategies.py")
        print("3. Run backtest: python examples/backtest_example.py")
        print("4. Start paper trading: python main.py")
        print("\nSee QUICKSTART.md for detailed instructions.")
    else:
        print("\n[FAILED] SOME CHECKS FAILED")
        print("\nPlease fix the issues above before running the bot.")
        print("\nCommon fixes:")
        print("- Install missing packages: pip install -r requirements.txt")
        print("- Verify all files are present")
        print("- Check for import errors")

    print("\n" + "="*70 + "\n")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
