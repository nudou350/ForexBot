"""
IBKR Connection Example for EUR/CAD Trading Bot
Demonstrates secure connection setup for both paper and live trading
"""

from ib_insync import IB, Forex, MarketOrder, StopOrder, Order
import time
from datetime import datetime
from typing import Optional, Tuple


class IBKRConnection:
    """
    IBKR connection manager with safety checks and error handling
    """

    def __init__(self, paper_trading: bool = True, client_id: int = 1):
        """
        Initialize IBKR connection

        Args:
            paper_trading: True for paper trading (port 7497), False for live (port 7496)
            client_id: Unique client ID for this connection (1-128)
        """
        self.ib = IB()
        self.paper_trading = paper_trading
        self.client_id = client_id
        self.port = 7497 if paper_trading else 7496
        self.host = '127.0.0.1'
        self.connected = False
        self.eurcad = None

        # Safety settings
        self.max_daily_loss = 500  # Maximum daily loss in account currency
        self.max_position_size = 100000  # Max position size in units
        self.daily_pnl = 0

    def connect(self, timeout: int = 20, retries: int = 3) -> bool:
        """
        Connect to IBKR with retry logic

        Args:
            timeout: Connection timeout in seconds
            retries: Number of connection attempts

        Returns:
            True if connected successfully, False otherwise
        """
        for attempt in range(retries):
            try:
                print(f"[{datetime.now()}] Connecting to IBKR (attempt {attempt + 1}/{retries})...")
                print(f"Mode: {'PAPER' if self.paper_trading else 'LIVE'} trading")
                print(f"Port: {self.port}")

                self.ib.connect(
                    host=self.host,
                    port=self.port,
                    clientId=self.client_id,
                    timeout=timeout
                )

                # Verify connection
                if self.ib.isConnected():
                    self.connected = True
                    print(f"✓ Connected successfully to IBKR")

                    # Setup EUR/CAD contract
                    self.eurcad = Forex('EURCAD')
                    self.ib.qualifyContracts(self.eurcad)
                    print(f"✓ EUR/CAD contract qualified")

                    # Setup disconnection handler
                    self.ib.disconnectedEvent += self._on_disconnected

                    # Get account summary
                    self._print_account_info()

                    return True

            except Exception as e:
                print(f"✗ Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < retries - 1:
                    wait_time = 5 * (attempt + 1)
                    print(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)

        print("✗ Failed to connect after all retries")
        return False

    def _on_disconnected(self):
        """Handle disconnection event"""
        print(f"\n[{datetime.now()}] ⚠ DISCONNECTED FROM IBKR!")
        self.connected = False

        # Close all positions if disconnected (safety)
        print("Attempting to reconnect...")
        if self.connect(retries=2):
            print("Reconnected successfully")
        else:
            print("Failed to reconnect. Manual intervention required.")

    def _print_account_info(self):
        """Print account information"""
        try:
            account = self.ib.managedAccounts()[0]
            account_values = self.ib.accountValues(account)

            print("\n=== Account Information ===")
            print(f"Account: {account}")

            for item in account_values:
                if item.tag in ['NetLiquidation', 'AvailableFunds', 'BuyingPower']:
                    print(f"{item.tag}: {item.value} {item.currency}")

            print("===========================\n")
        except Exception as e:
            print(f"Could not retrieve account info: {e}")

    def get_current_price(self) -> Optional[Tuple[float, float, float]]:
        """
        Get current market price for EUR/CAD

        Returns:
            Tuple of (bid, ask, mid) or None if data unavailable
        """
        if not self.connected:
            print("Not connected to IBKR")
            return None

        try:
            ticker = self.ib.reqMktData(self.eurcad, '', False, False)
            self.ib.sleep(2)  # Wait for data to populate

            if ticker.bid and ticker.ask:
                bid = ticker.bid
                ask = ticker.ask
                mid = (bid + ask) / 2
                return (bid, ask, mid)
            else:
                print("Market data not available")
                return None

        except Exception as e:
            print(f"Error getting market data: {e}")
            return None

    def place_market_order(
        self,
        action: str,
        quantity: int,
        stop_loss_pips: Optional[int] = None
    ) -> Optional[Order]:
        """
        Place market order with optional stop loss

        Args:
            action: 'BUY' or 'SELL'
            quantity: Position size in units
            stop_loss_pips: Stop loss distance in pips (optional)

        Returns:
            Order object or None if order failed
        """
        if not self.connected:
            print("Not connected to IBKR")
            return None

        # Safety checks
        if not self._safety_checks(quantity):
            return None

        try:
            # Get current price
            price_data = self.get_current_price()
            if not price_data:
                print("Cannot place order: No market data")
                return None

            bid, ask, mid = price_data
            entry_price = ask if action == 'BUY' else bid

            print(f"\n=== Placing Order ===")
            print(f"Action: {action}")
            print(f"Quantity: {quantity} units ({quantity / 100000:.2f} lots)")
            print(f"Entry Price: {entry_price:.5f}")

            # Create market order
            order = MarketOrder(action, quantity)

            # Place order
            trade = self.ib.placeOrder(self.eurcad, order)

            # Wait for order to fill
            timeout = 30
            elapsed = 0
            while not trade.isDone() and elapsed < timeout:
                self.ib.sleep(0.5)
                elapsed += 0.5

            if trade.orderStatus.status == 'Filled':
                filled_price = trade.orderStatus.avgFillPrice
                print(f"✓ Order filled at {filled_price:.5f}")

                # Place stop loss if specified
                if stop_loss_pips:
                    self._place_stop_loss(action, quantity, filled_price, stop_loss_pips)

                return trade.order

            else:
                print(f"✗ Order not filled: {trade.orderStatus.status}")
                return None

        except Exception as e:
            print(f"✗ Error placing order: {e}")
            return None

    def _place_stop_loss(
        self,
        original_action: str,
        quantity: int,
        entry_price: float,
        stop_pips: int
    ):
        """Place stop loss order"""
        try:
            # Calculate stop price
            pip_size = 0.0001
            stop_action = 'SELL' if original_action == 'BUY' else 'BUY'

            if original_action == 'BUY':
                stop_price = entry_price - (stop_pips * pip_size)
            else:
                stop_price = entry_price + (stop_pips * pip_size)

            print(f"Placing stop loss at {stop_price:.5f} ({stop_pips} pips)")

            # Create stop order
            stop_order = StopOrder(stop_action, quantity, stop_price)

            # Place stop order
            stop_trade = self.ib.placeOrder(self.eurcad, stop_order)
            print(f"✓ Stop loss placed successfully")

        except Exception as e:
            print(f"✗ Error placing stop loss: {e}")

    def _safety_checks(self, quantity: int) -> bool:
        """
        Perform safety checks before placing order

        Args:
            quantity: Position size to check

        Returns:
            True if all checks pass, False otherwise
        """
        # Check if live trading
        if not self.paper_trading:
            print("\n⚠ WARNING: LIVE TRADING MODE")
            print("Performing additional safety checks...")

        # Check position size
        if quantity > self.max_position_size:
            print(f"✗ Position size {quantity} exceeds maximum {self.max_position_size}")
            return False

        # Check daily loss limit
        if abs(self.daily_pnl) >= self.max_daily_loss:
            print(f"✗ Daily loss limit reached: {self.daily_pnl}")
            return False

        # Check account margin
        try:
            account = self.ib.managedAccounts()[0]
            account_values = self.ib.accountValues(account)

            buying_power = 0
            for item in account_values:
                if item.tag == 'BuyingPower':
                    buying_power = float(item.value)
                    break

            if buying_power < 1000:  # Minimum margin requirement
                print(f"✗ Insufficient buying power: {buying_power}")
                return False

        except Exception as e:
            print(f"⚠ Could not verify margin: {e}")

        return True

    def get_positions(self):
        """Get current open positions"""
        if not self.connected:
            print("Not connected to IBKR")
            return []

        try:
            positions = self.ib.positions()

            print("\n=== Current Positions ===")
            if not positions:
                print("No open positions")
            else:
                for pos in positions:
                    if 'EUR' in pos.contract.symbol and 'CAD' in pos.contract.symbol:
                        print(f"{pos.contract.symbol}: {pos.position} units @ {pos.avgCost:.5f}")
            print("=========================\n")

            return positions

        except Exception as e:
            print(f"Error getting positions: {e}")
            return []

    def close_all_positions(self):
        """Emergency: Close all EUR/CAD positions"""
        if not self.connected:
            print("Not connected to IBKR")
            return

        print("\n⚠ CLOSING ALL EUR/CAD POSITIONS ⚠")

        try:
            positions = self.ib.positions()

            for pos in positions:
                if 'EUR' in pos.contract.symbol and 'CAD' in pos.contract.symbol:
                    quantity = abs(pos.position)
                    action = 'SELL' if pos.position > 0 else 'BUY'

                    print(f"Closing {pos.position} units of {pos.contract.symbol}")

                    order = MarketOrder(action, quantity)
                    trade = self.ib.placeOrder(pos.contract, order)

                    # Wait for fill
                    timeout = 30
                    elapsed = 0
                    while not trade.isDone() and elapsed < timeout:
                        self.ib.sleep(0.5)
                        elapsed += 0.5

                    if trade.orderStatus.status == 'Filled':
                        print(f"✓ Position closed")
                    else:
                        print(f"✗ Failed to close position: {trade.orderStatus.status}")

        except Exception as e:
            print(f"Error closing positions: {e}")

    def disconnect(self):
        """Disconnect from IBKR"""
        if self.connected:
            print(f"\n[{datetime.now()}] Disconnecting from IBKR...")
            self.ib.disconnect()
            self.connected = False
            print("Disconnected successfully")


# Example usage
if __name__ == "__main__":
    # Initialize connection (paper trading)
    ibkr = IBKRConnection(paper_trading=True, client_id=1)

    # Connect
    if ibkr.connect():
        # Get current price
        price = ibkr.get_current_price()
        if price:
            bid, ask, mid = price
            print(f"\nEUR/CAD Price: Bid={bid:.5f}, Ask={ask:.5f}, Mid={mid:.5f}")

        # Check current positions
        ibkr.get_positions()

        # Example: Place a market order (commented out for safety)
        # ibkr.place_market_order('BUY', 20000, stop_loss_pips=25)

        # Keep connection alive
        print("\nConnection established. Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            ibkr.close_all_positions()  # Optional: close positions on exit
            ibkr.disconnect()
    else:
        print("Failed to establish connection")
