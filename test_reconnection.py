"""
Test script to verify reconnection logic
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.ibkr.connector import IBKRConnector
from config import config

def test_reconnection():
    """Test the reconnection functionality"""

    print("=== Testing IBKR Reconnection Logic ===\n")

    # Create connector
    connector = IBKRConnector()

    # Test 1: Initial connection
    print("Test 1: Initial connection")
    if connector.connect():
        print("✅ Initial connection successful")
    else:
        print("❌ Initial connection failed")
        return

    print(f"Connected: {connector.is_connected}")
    print(f"Reconnect attempts: {connector.reconnect_attempts}\n")

    # Test 2: Check connection health
    print("Test 2: Connection health check")
    if connector.check_connection():
        print("✅ Connection is healthy")
    else:
        print("❌ Connection is not healthy")

    print(f"Connected: {connector.is_connected}\n")

    # Test 3: Ensure connection (should pass without reconnecting)
    print("Test 3: Ensure connection (already connected)")
    if connector.ensure_connection():
        print("✅ Connection ensured (no reconnection needed)")
    else:
        print("❌ Failed to ensure connection")

    print(f"Reconnect attempts: {connector.reconnect_attempts}\n")

    # Test 4: Fetch data
    print("Test 4: Fetch historical data")
    df = connector.get_historical_data()
    if df is not None and len(df) > 0:
        print(f"✅ Successfully fetched {len(df)} bars of data")
        print(f"Data range: {df.index[0]} to {df.index[-1]}")
    else:
        print("❌ Failed to fetch data")

    print()

    # Test 5: Simulate disconnect and reconnect
    print("Test 5: Simulate disconnect and reconnect")
    print("Disconnecting...")
    connector.disconnect()
    print(f"Connected: {connector.is_connected}")

    print("\nAttempting to ensure connection (should trigger reconnect)...")
    if connector.ensure_connection():
        print("✅ Successfully reconnected")
        print(f"Reconnect attempts used: {connector.reconnect_attempts}")
    else:
        print("❌ Failed to reconnect")

    print()

    # Test 6: Fetch data after reconnection
    print("Test 6: Fetch data after reconnection")
    df = connector.get_historical_data()
    if df is not None and len(df) > 0:
        print(f"✅ Successfully fetched {len(df)} bars of data after reconnection")
    else:
        print("❌ Failed to fetch data after reconnection")

    # Cleanup
    print("\nCleaning up...")
    connector.disconnect()
    print("✅ Test complete")

if __name__ == "__main__":
    test_reconnection()
