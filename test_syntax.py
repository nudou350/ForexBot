"""
Quick syntax and import test (doesn't require IBKR connection)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

print("Testing imports and syntax...\n")

# Test 1: Import connector
try:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from src.ibkr.connector import IBKRConnector
    print("✅ IBKRConnector import successful")
except Exception as e:
    print(f"❌ IBKRConnector import failed: {e}")
    exit(1)

# Test 2: Import emergency stop
try:
    from src.risk_management.emergency_stop import EmergencyStopSystem
    print("✅ EmergencyStopSystem import successful")
except Exception as e:
    print(f"❌ EmergencyStopSystem import failed: {e}")
    exit(1)

# Test 3: Import risk manager
try:
    from src.risk_management.risk_manager import RiskManager
    print("✅ RiskManager import successful")
except Exception as e:
    print(f"❌ RiskManager import failed: {e}")
    exit(1)

# Test 4: Check connector has new methods
try:
    connector = IBKRConnector()
    assert hasattr(connector, 'check_connection'), "Missing check_connection method"
    assert hasattr(connector, 'reconnect'), "Missing reconnect method"
    assert hasattr(connector, 'ensure_connection'), "Missing ensure_connection method"
    assert hasattr(connector, 'reconnect_attempts'), "Missing reconnect_attempts attribute"
    assert hasattr(connector, 'max_reconnect_attempts'), "Missing max_reconnect_attempts attribute"
    print("✅ All new connector methods present")
except Exception as e:
    print(f"❌ Connector methods check failed: {e}")
    exit(1)

# Test 5: Check emergency stop has new attributes
try:
    from src.risk_management.risk_manager import RiskManager
    rm = RiskManager(10000)
    es = EmergencyStopSystem(rm)
    assert hasattr(es, 'consecutive_api_errors'), "Missing consecutive_api_errors attribute"
    assert hasattr(es, 'max_consecutive_errors'), "Missing max_consecutive_errors attribute"
    assert hasattr(es, 'error_reset_threshold'), "Missing error_reset_threshold attribute"
    print("✅ All new emergency stop attributes present")
except Exception as e:
    print(f"❌ Emergency stop attributes check failed: {e}")
    exit(1)

# Test 6: Test method signatures
try:
    # Test log_api_error doesn't crash
    es.log_api_error()
    assert es.consecutive_api_errors == 1, "log_api_error didn't increment consecutive"
    assert es.api_error_count == 1, "log_api_error didn't increment total"

    # Test reset_api_errors
    es.reset_api_errors()
    assert es.consecutive_api_errors == 0, "reset_api_errors didn't reset consecutive"
    assert es.api_error_count == 1, "reset_api_errors incorrectly reset total"

    print("✅ Error tracking logic works correctly")
except Exception as e:
    print(f"❌ Error tracking test failed: {e}")
    exit(1)

# Test 7: Test auto-reset threshold
try:
    es.api_error_count = 150  # Set high
    es.consecutive_api_errors = 5
    es.log_api_error()  # This should trigger auto-reset

    # After reset, total should be reset to consecutive count
    assert es.api_error_count <= 10, f"Auto-reset didn't work: {es.api_error_count}"
    print("✅ Auto-reset threshold works correctly")
except Exception as e:
    print(f"❌ Auto-reset test failed: {e}")
    exit(1)

print("\n" + "="*50)
print("All tests passed! ✅")
print("="*50)
print("\nThe bot is ready to run.")
print("Note: Connection test skipped (requires IBKR Gateway)")
