"""
IBKR TWS API Connector for EUR/CAD Trading Bot
Handles connection, data fetching, and order management
"""

from ib_insync import *
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config


class IBKRConnector:
    """
    Interactive Brokers API connector for EUR/CAD trading
    Handles connection, data, and order management
    """

    def __init__(self, host: str = None, port: int = None, client_id: int = None):
        """
        Initialize IBKR connection

        Args:
            host: IBKR host address (default from config)
            port: Port number (7497 for paper, 7496 for live)
            client_id: Client ID for connection
        """
        self.ib = IB()
        self.host = host or config.IBKR_HOST
        self.port = port or (config.IBKR_PAPER_PORT if config.PAPER_TRADING
                            else config.IBKR_LIVE_PORT)
        self.client_id = client_id or config.IBKR_CLIENT_ID
        self.contract: Optional[Forex] = None
        self.is_connected = False
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """
        Connect to IBKR TWS or Gateway

        Returns:
            True if connected successfully
        """
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.is_connected = True
            self.logger.info(f"Connected to IBKR on {self.host}:{self.port}")
            print(f"Connected to IBKR on port {self.port}")

            # Setup EUR/CAD contract
            self.contract = Forex('EURCAD')
            self.ib.qualifyContracts(self.contract)

            return True

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            print(f"Connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from IBKR"""
        if self.is_connected:
            self.ib.disconnect()
            self.is_connected = False
            self.logger.info("Disconnected from IBKR")
            print("Disconnected from IBKR")

    def get_historical_data(self, duration: str = None,
                           bar_size: str = None) -> Optional[pd.DataFrame]:
        """
        Get historical data for EUR/CAD

        Args:
            duration: Duration string (e.g., '1 D', '5 D', '1 W', '1 M')
            bar_size: Bar size (e.g., '1 min', '1 hour', '1 day')

        Returns:
            DataFrame with OHLCV data or None
        """
        duration = duration or config.HISTORICAL_DATA_DURATION
        bar_size = bar_size or config.HISTORICAL_DATA_BARSIZE

        try:
            bars = self.ib.reqHistoricalData(
                self.contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='MIDPOINT',
                useRTH=False,  # Include overnight data
                formatDate=1
            )

            if not bars:
                self.logger.warning("No historical data received")
                return None

            # Convert to DataFrame
            df = util.df(bars)
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume',
                         'average', 'barCount']
            df.set_index('date', inplace=True)

            self.logger.info(f"Fetched {len(df)} bars of historical data")
            return df[['open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            self.logger.error(f"Error fetching historical data: {e}")
            return None

    def get_current_price(self) -> Optional[Dict]:
        """
        Get current bid/ask/last price for EUR/CAD

        Returns:
            Dictionary with price data or None
        """
        try:
            ticker = self.ib.reqTicker(self.contract)
            self.ib.sleep(1)  # Wait for data

            return {
                'bid': ticker.bid,
                'ask': ticker.ask,
                'last': ticker.last,
                'mid': (ticker.bid + ticker.ask) / 2 if ticker.bid and ticker.ask else None,
                'timestamp': datetime.now()
            }

        except Exception as e:
            self.logger.error(f"Error fetching current price: {e}")
            return None

    def place_market_order(self, action: str, quantity: int) -> Optional[Trade]:
        """
        Place market order

        Args:
            action: 'BUY' or 'SELL'
            quantity: Number of units (e.g., 100000 for 1 standard lot)

        Returns:
            Trade object or None
        """
        try:
            order = MarketOrder(action, quantity)
            trade = self.ib.placeOrder(self.contract, order)

            self.logger.info(f"Market order placed: {action} {quantity} EUR/CAD")
            print(f"Market order placed: {action} {quantity} EUR/CAD")

            return trade

        except Exception as e:
            self.logger.error(f"Error placing market order: {e}")
            return None

    def place_bracket_order(self, action: str, quantity: int,
                           take_profit_price: float,
                           stop_loss_price: float) -> Optional[List]:
        """
        Place bracket order (entry + TP + SL)

        Args:
            action: 'BUY' or 'SELL'
            quantity: Number of units
            take_profit_price: Take profit price
            stop_loss_price: Stop loss price

        Returns:
            List of orders or None
        """
        try:
            # Create parent order
            parent = MarketOrder(action, quantity)

            # Create take profit order
            take_profit_action = 'SELL' if action == 'BUY' else 'BUY'
            take_profit = LimitOrder(take_profit_action, quantity, take_profit_price)

            # Create stop loss order
            stop_loss = StopOrder(take_profit_action, quantity, stop_loss_price)

            # Bracket order
            bracket_orders = self.ib.bracketOrder(
                'BUY' if action == 'BUY' else 'SELL',
                quantity,
                limitPrice=take_profit_price,
                stopPrice=stop_loss_price
            )

            # Place orders
            trades = []
            for order in bracket_orders:
                trade = self.ib.placeOrder(self.contract, order)
                trades.append(trade)

            self.logger.info(
                f"Bracket order placed: {action} {quantity} EUR/CAD, "
                f"TP: {take_profit_price}, SL: {stop_loss_price}"
            )
            print(
                f"Bracket order placed: {action} {quantity} EUR/CAD\n"
                f"  TP: {take_profit_price}, SL: {stop_loss_price}"
            )

            return trades

        except Exception as e:
            self.logger.error(f"Error placing bracket order: {e}")
            return None

    def modify_stop_loss(self, order_id: int, new_stop_price: float) -> bool:
        """
        Modify stop loss (for trailing stops)

        Args:
            order_id: Order ID to modify
            new_stop_price: New stop loss price

        Returns:
            True if successful
        """
        try:
            orders = self.ib.orders()
            for order in orders:
                if order.orderId == order_id:
                    order.auxPrice = new_stop_price
                    self.ib.placeOrder(self.contract, order)
                    self.logger.info(f"Stop loss updated to {new_stop_price}")
                    return True

            self.logger.warning(f"Order {order_id} not found")
            return False

        except Exception as e:
            self.logger.error(f"Error modifying stop loss: {e}")
            return False

    def cancel_order(self, order_id: int) -> bool:
        """
        Cancel specific order

        Args:
            order_id: Order ID to cancel

        Returns:
            True if successful
        """
        try:
            orders = self.ib.orders()
            for order in orders:
                if order.orderId == order_id:
                    self.ib.cancelOrder(order)
                    self.logger.info(f"Order {order_id} cancelled")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            return False

    def cancel_all_orders(self) -> bool:
        """
        Cancel all open orders

        Returns:
            True if successful
        """
        try:
            self.ib.reqGlobalCancel()
            self.logger.info("All orders cancelled")
            print("All orders cancelled")
            return True

        except Exception as e:
            self.logger.error(f"Error cancelling orders: {e}")
            return False

    def get_positions(self) -> List:
        """
        Get all current positions

        Returns:
            List of Position objects
        """
        try:
            positions = self.ib.positions()
            return positions

        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []

    def get_account_summary(self) -> Optional[Dict]:
        """
        Get account balance and key metrics

        Returns:
            Dictionary with account data or None
        """
        try:
            account_values = self.ib.accountSummary()

            summary = {}
            for av in account_values:
                summary[av.tag] = av.value

            result = {
                'net_liquidation': float(summary.get('NetLiquidation', 0)),
                'total_cash': float(summary.get('TotalCashValue', 0)),
                'unrealized_pnl': float(summary.get('UnrealizedPnL', 0)),
                'realized_pnl': float(summary.get('RealizedPnL', 0)),
            }

            self.logger.info(f"Account balance: ${result['net_liquidation']:.2f}")
            return result

        except Exception as e:
            self.logger.error(f"Error getting account summary: {e}")
            return None

    def get_open_orders(self) -> List:
        """
        Get all open orders

        Returns:
            List of Order objects
        """
        try:
            return self.ib.openOrders()

        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return []

    def wait_for_order_fill(self, trade: Trade, timeout: int = 30) -> bool:
        """
        Wait for order to be filled

        Args:
            trade: Trade object to monitor
            timeout: Timeout in seconds

        Returns:
            True if filled
        """
        try:
            filled = False
            for _ in range(timeout):
                self.ib.sleep(1)
                if trade.orderStatus.status == 'Filled':
                    filled = True
                    break

            return filled

        except Exception as e:
            self.logger.error(f"Error waiting for order fill: {e}")
            return False
