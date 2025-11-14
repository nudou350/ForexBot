"""
Main EUR/CAD Trading Bot
Orchestrates all components for automated trading
"""

import time
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional
import sys
import os
import json
import threading

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import config
from src.ibkr.connector import IBKRConnector
from src.risk_management.risk_manager import RiskManager
from src.risk_management.emergency_stop import EmergencyStopSystem
from src.market_analysis.regime_detector import MarketRegimeDetector
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.trend_following import TrendFollowingStrategy
from src.strategies.grid_trading import GridTradingStrategy


class EURCADTradingBot:
    """
    Main trading bot orchestrating all components
    """

    def __init__(self, initial_capital: float = None, paper_trading: bool = None):
        """
        Initialize trading bot

        Args:
            initial_capital: Starting capital
            paper_trading: Use paper trading (default from config)
        """
        self.initial_capital = initial_capital or config.INITIAL_CAPITAL
        self.paper_trading = (paper_trading if paper_trading is not None
                             else config.PAPER_TRADING)

        # Initialize components
        port = config.IBKR_PAPER_PORT if self.paper_trading else config.IBKR_LIVE_PORT
        self.ibkr = IBKRConnector(port=port)
        self.risk_manager = RiskManager(self.initial_capital)
        self.emergency_stop = EmergencyStopSystem(self.risk_manager)
        self.regime_detector = MarketRegimeDetector()

        # Strategies
        self.strategies = {
            'mean_reversion': MeanReversionStrategy(),
            'trend_following': TrendFollowingStrategy(),
            'grid_trading': GridTradingStrategy(total_capital=self.initial_capital)
        }

        self.active_strategy = None
        self.current_regime = None

        # Setup logging
        logging.basicConfig(
            filename=config.LOG_FILE,
            level=getattr(logging, config.LOG_LEVEL),
            format=config.LOG_FORMAT
        )
        self.logger = logging.getLogger(__name__)

        # State file for dashboard
        self.state_file = 'bot_state.json'
        self.closed_trades = []  # Track all closed trades
        self.dashboard_thread = None  # Dashboard thread

    def start_dashboard(self) -> None:
        """Start the dashboard in a background thread"""
        if not config.ENABLE_DASHBOARD:
            return

        try:
            from src.dashboard.dashboard import TradingDashboard

            def run_dashboard():
                dashboard = TradingDashboard(port=config.DASHBOARD_PORT)
                dashboard.run(show_banner=False)

            self.dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
            self.dashboard_thread.start()

            print(f"\n{'='*50}")
            print(f"  Dashboard started!")
            print(f"  Open your browser: http://localhost:{config.DASHBOARD_PORT}")
            print(f"{'='*50}\n")

            self.logger.info(f"Dashboard started on port {config.DASHBOARD_PORT}")

        except Exception as e:
            self.logger.error(f"Failed to start dashboard: {e}")
            print(f"Warning: Dashboard failed to start: {e}")
            print("Bot will continue without dashboard.\n")

    def save_state(self) -> None:
        """Save current bot state to JSON file for dashboard"""
        try:
            # Calculate win rate
            total_trades = len(self.closed_trades)
            wins = sum(1 for t in self.closed_trades if t.get('pnl', 0) > 0)
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

            # Build equity curve
            equity_curve = [self.initial_capital]
            running_capital = self.initial_capital
            for trade in self.closed_trades:
                running_capital += trade.get('pnl', 0)
                equity_curve.append(running_capital)

            state = {
                'status': 'Running' if not self.risk_manager.trading_halted else 'Halted',
                'current_capital': self.risk_manager.current_capital,
                'win_rate': win_rate,
                'total_trades': total_trades,
                'open_positions': len(self.risk_manager.open_positions),
                'market_regime': self.current_regime or 'N/A',
                'active_strategy': self.active_strategy.name if self.active_strategy else 'N/A',
                'equity_curve': equity_curve,
                'trades': self.closed_trades,
                'last_update': datetime.now().isoformat()
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving state: {e}")

    def start(self) -> None:
        """Start the trading bot"""
        mode = "PAPER TRADING" if self.paper_trading else "LIVE TRADING"
        self.logger.info(f"Starting EUR/CAD Trading Bot - {mode}")
        print(f"\nStarting EUR/CAD Trading Bot - {mode}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}\n")

        # Connect to IBKR
        if not self.ibkr.connect():
            self.logger.error("Failed to connect to IBKR")
            print("Failed to connect to IBKR. Please ensure TWS/Gateway is running.")
            return

        self.logger.info("Connected to IBKR successfully")

        # Start dashboard if enabled
        self.start_dashboard()

        # Give dashboard a moment to start
        if config.ENABLE_DASHBOARD:
            time.sleep(2)

        # Main trading loop
        try:
            while True:
                self.trading_cycle()
                time.sleep(60)  # Run every minute

        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
            print("\nBot stopped by user")
            self.stop()

        except Exception as e:
            self.logger.error(f"Critical error: {e}", exc_info=True)
            print(f"\nCritical error: {e}")
            self.stop()

    def trading_cycle(self) -> None:
        """Execute one trading cycle"""
        current_time = datetime.now()

        # Check if trading should be active
        is_trading_hours, reason = self.emergency_stop.check_trading_hours(current_time)
        if not is_trading_hours:
            return

        # Get market data
        df = self.ibkr.get_historical_data()
        if df is None or len(df) < config.MIN_DATA_POINTS:
            self.logger.warning("Insufficient data")
            self.emergency_stop.log_api_error()
            return

        # Reset API errors on successful data fetch
        self.emergency_stop.reset_api_errors()
        self.emergency_stop.update_price_timestamp(current_time)

        # Check emergency conditions
        should_stop, stop_reason = self.emergency_stop.check_emergency_conditions(
            df, current_time
        )
        if should_stop:
            self.risk_manager.halt_trading(stop_reason)
            self.logger.warning(f"Emergency stop triggered: {stop_reason}")
            return

        # Detect market regime
        self.current_regime = self.regime_detector.detect_regime(df)
        self.logger.info(f"Market regime: {self.current_regime}")

        # Select strategy
        strategy_name, params = self.select_strategy(self.current_regime)
        if strategy_name == 'stay_out':
            self.logger.info("High volatility - staying out")
            return

        self.active_strategy = self.strategies[strategy_name]
        self.logger.info(f"Active strategy: {strategy_name}")

        # Generate signals
        df = self.active_strategy.generate_signals(df)

        # Check for entry signals
        if df['long_signal'].iloc[-1] if 'long_signal' in df.columns else False:
            self.process_signal('long', df, params)
        elif df['short_signal'].iloc[-1] if 'short_signal' in df.columns else False:
            self.process_signal('short', df, params)

        # Manage open positions
        self.manage_positions(df)

        # Save state for dashboard
        self.save_state()

    def select_strategy(self, regime: str) -> Tuple[str, Dict]:
        """
        Select strategy based on market regime

        Args:
            regime: Market regime type

        Returns:
            Tuple of (strategy_name, parameters)
        """
        if regime == 'STRONG_TREND':
            return 'trend_following', {'risk': config.TREND_FOLLOWING_RISK}
        elif regime in ['RANGING', 'WEAK_TREND']:
            return 'mean_reversion', {'risk': config.MEAN_REVERSION_RISK}
        elif regime == 'LOW_VOLATILITY':
            return 'grid_trading', {'risk': config.GRID_TRADING_RISK}
        elif regime == 'HIGH_VOLATILITY':
            return 'stay_out', {'risk': 0}
        else:
            return 'mean_reversion', {'risk': config.MEAN_REVERSION_RISK}

    def process_signal(self, signal_type: str, df, params: Dict) -> None:
        """
        Process trading signal and place order if conditions met

        Args:
            signal_type: 'long' or 'short'
            df: DataFrame with market data
            params: Strategy parameters
        """
        # Calculate entry/exit levels
        entry_data = self.active_strategy.calculate_entry_exit(df, signal_type)
        if not entry_data:
            self.logger.info(f"No valid entry data for {signal_type} signal")
            return

        # Calculate position size
        entry_price = entry_data['entry']
        stop_loss = entry_data['stop_loss']
        risk_amount = self.risk_manager.current_capital * params['risk']

        position_size = self.risk_manager.calculate_position_size(
            entry_price, stop_loss, params['risk']
        )

        if position_size == 0:
            self.logger.warning("Position size is 0 - skipping trade")
            return

        # Check if position can be opened
        can_open, reason = self.risk_manager.can_open_position(
            risk_amount, self.active_strategy.name
        )

        if not can_open:
            self.logger.warning(f"Position blocked: {reason}")
            return

        # Check spread
        price_data = self.ibkr.get_current_price()
        if price_data:
            is_acceptable, spread_reason = self.emergency_stop.check_spread_conditions(
                price_data['bid'], price_data['ask']
            )
            if not is_acceptable:
                self.logger.warning(f"Spread check failed: {spread_reason}")
                return

        # Place order
        action = 'BUY' if signal_type == 'long' else 'SELL'
        quantity = int(position_size * 100000)  # Convert lots to units

        if quantity < 20000:  # Minimum trade size
            self.logger.warning(f"Position size too small: {quantity} units")
            return

        trade = self.ibkr.place_bracket_order(
            action=action,
            quantity=quantity,
            take_profit_price=entry_data['take_profit_1'],
            stop_loss_price=stop_loss
        )

        if trade:
            # Record position
            position = {
                'id': trade[0].orderId if hasattr(trade[0], 'orderId') else None,
                'type': signal_type,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': entry_data['take_profit_1'],
                'size': position_size,
                'risk_amount': risk_amount,
                'strategy': self.active_strategy.name,
                'entry_time': datetime.now()
            }

            self.risk_manager.add_position(position)

            self.logger.info(
                f"{signal_type.upper()} position opened: "
                f"{position_size:.2f} lots at {entry_price:.5f}"
            )
            print(
                f"\n{signal_type.upper()} position opened:"
                f"\n  Size: {position_size:.2f} lots"
                f"\n  Entry: {entry_price:.5f}"
                f"\n  Stop Loss: {stop_loss:.5f}"
                f"\n  Take Profit: {entry_data['take_profit_1']:.5f}"
                f"\n  Risk/Reward: {entry_data.get('risk_reward_1', 0):.2f}:1\n"
            )

    def manage_positions(self, df) -> None:
        """
        Manage open positions (trailing stops, partial profits)

        Args:
            df: DataFrame with market data
        """
        positions = self.ibkr.get_positions()

        for pos in self.risk_manager.open_positions:
            # Check if position is still open in IBKR
            ibkr_pos = next(
                (p for p in positions if p.contract.symbol == 'EUR' and
                 p.contract.currency == 'CAD'),
                None
            )

            if not ibkr_pos:
                # Position was closed
                continue

            # Implement trailing stop for trend following
            if pos['strategy'] == 'Trend Following':
                self.update_trailing_stop(pos, df)

    def update_trailing_stop(self, position: Dict, df) -> None:
        """
        Update trailing stop for trend following

        Args:
            position: Position dictionary
            df: DataFrame with market data
        """
        if 'ATR' not in df.columns:
            return

        current_price = df['close'].iloc[-1]
        atr = df['ATR'].iloc[-1]

        if position['type'] == 'long':
            new_stop = current_price - (config.TRAILING_STOP_ATR_MULTIPLE * atr)
            if new_stop > position['stop_loss']:
                if position.get('id'):
                    self.ibkr.modify_stop_loss(position['id'], new_stop)
                position['stop_loss'] = new_stop
                self.logger.info(f"Trailing stop updated to {new_stop:.5f}")

        else:  # short
            new_stop = current_price + (config.TRAILING_STOP_ATR_MULTIPLE * atr)
            if new_stop < position['stop_loss']:
                if position.get('id'):
                    self.ibkr.modify_stop_loss(position['id'], new_stop)
                position['stop_loss'] = new_stop
                self.logger.info(f"Trailing stop updated to {new_stop:.5f}")

    def stop(self) -> None:
        """Stop the bot and cleanup"""
        self.logger.info("Stopping bot")
        print("\nStopping bot...")

        # Cancel all pending orders
        self.ibkr.cancel_all_orders()

        # Print final summary
        summary = self.risk_manager.get_account_summary()
        print("\n" + "="*50)
        print("FINAL SUMMARY")
        print("="*50)
        print(f"Initial Capital: ${summary['initial_capital']:,.2f}")
        print(f"Final Capital: ${summary['current_capital']:,.2f}")
        print(f"Total Return: {summary['total_return']:.2%}")
        print(f"Max Drawdown: {summary['current_drawdown']:.2%}")
        print(f"Total Trades: {summary['daily_trade_count']}")
        print("="*50 + "\n")

        # Disconnect
        self.ibkr.disconnect()

        self.logger.info("Bot stopped successfully")


def main():
    """Main entry point"""
    # Configuration
    bot = EURCADTradingBot(
        initial_capital=config.INITIAL_CAPITAL,
        paper_trading=config.PAPER_TRADING
    )

    mode = "PAPER TRADING" if config.PAPER_TRADING else "LIVE TRADING"

    print("""
    =========================================
       EUR/CAD TRADING BOT - STARTED
    =========================================
       Platform: Interactive Brokers
       Mode: """ + f"{mode:^28}" + """
       Initial Capital: """ + f"${config.INITIAL_CAPITAL:>13,.2f}" + """

       Target: 65-75%% Win Rate
       Max Drawdown: 12%%

       Press Ctrl+C to stop
    =========================================
    """)

    bot.start()


if __name__ == "__main__":
    main()
