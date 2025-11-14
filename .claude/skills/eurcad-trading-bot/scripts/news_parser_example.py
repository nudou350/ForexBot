"""
News Parser Example for EUR/CAD Trading Bot
Fetches and parses economic calendar data to avoid trading during high-impact events
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time


class EconomicCalendar:
    """
    Economic calendar parser for Forex Factory and Trading Economics
    Filters high-impact EUR and CAD events
    """

    def __init__(self):
        self.forex_factory_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        self.events_cache = []
        self.cache_time = None
        self.cache_duration = 3600  # Cache for 1 hour

    def fetch_forex_factory_events(self) -> List[Dict]:
        """
        Fetch events from Forex Factory calendar

        Returns:
            List of economic events
        """
        try:
            print("Fetching events from Forex Factory...")
            response = requests.get(self.forex_factory_url, timeout=10)
            response.raise_for_status()

            events = response.json()
            print(f"✓ Fetched {len(events)} events")

            return events

        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching Forex Factory data: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing JSON: {e}")
            return []

    def filter_high_impact_events(self, events: List[Dict]) -> List[Dict]:
        """
        Filter for high-impact EUR and CAD events

        Args:
            events: List of all events

        Returns:
            Filtered list of high-impact EUR/CAD events
        """
        filtered = []

        for event in events:
            try:
                # Check if event has required fields
                if 'country' not in event or 'impact' not in event:
                    continue

                country = event.get('country', '').upper()
                impact = event.get('impact', '').lower()

                # Filter for EUR and CAD high-impact events
                if country in ['EUR', 'CAD'] and impact in ['high', 'medium']:
                    filtered.append(event)

            except Exception as e:
                print(f"Error processing event: {e}")
                continue

        print(f"Filtered to {len(filtered)} high-impact EUR/CAD events")
        return filtered

    def get_upcoming_events(self, hours_ahead: int = 24) -> List[Dict]:
        """
        Get upcoming high-impact events within specified timeframe

        Args:
            hours_ahead: Look ahead window in hours

        Returns:
            List of upcoming events
        """
        # Check cache
        if self.cache_time and self.events_cache:
            time_since_cache = (datetime.now() - self.cache_time).total_seconds()
            if time_since_cache < self.cache_duration:
                print("Using cached events")
                return self._filter_by_time(self.events_cache, hours_ahead)

        # Fetch fresh data
        all_events = self.fetch_forex_factory_events()
        filtered_events = self.filter_high_impact_events(all_events)

        # Update cache
        self.events_cache = filtered_events
        self.cache_time = datetime.now()

        return self._filter_by_time(filtered_events, hours_ahead)

    def _filter_by_time(self, events: List[Dict], hours_ahead: int) -> List[Dict]:
        """Filter events by time window"""
        now = datetime.now()
        future_cutoff = now + timedelta(hours=hours_ahead)

        upcoming = []
        for event in events:
            try:
                # Parse event time
                event_time_str = event.get('date', '')
                if not event_time_str:
                    continue

                # Try different date formats
                for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                    try:
                        event_time = datetime.strptime(event_time_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # If no format worked, skip
                    continue

                # Check if event is in time window
                if now <= event_time <= future_cutoff:
                    upcoming.append({
                        'title': event.get('title', 'Unknown'),
                        'country': event.get('country', ''),
                        'impact': event.get('impact', ''),
                        'time': event_time,
                        'forecast': event.get('forecast', ''),
                        'previous': event.get('previous', '')
                    })

            except Exception as e:
                print(f"Error parsing event time: {e}")
                continue

        # Sort by time
        upcoming.sort(key=lambda x: x['time'])

        return upcoming

    def is_safe_to_trade(self, blackout_before_mins: int = 5, blackout_after_mins: int = 2) -> tuple:
        """
        Check if it's safe to trade (no high-impact news nearby)

        Args:
            blackout_before_mins: Minutes before event to stop trading
            blackout_after_mins: Minutes after event to resume trading

        Returns:
            Tuple (is_safe: bool, reason: str, next_event: Optional[Dict])
        """
        upcoming_events = self.get_upcoming_events(hours_ahead=2)

        if not upcoming_events:
            return (True, "No high-impact events in next 2 hours", None)

        now = datetime.now()

        for event in upcoming_events:
            event_time = event['time']
            time_diff_minutes = (event_time - now).total_seconds() / 60

            # Check if we're in blackout period before event
            if 0 <= time_diff_minutes <= blackout_before_mins:
                reason = f"{event['country']} {event['impact']}-impact event '{event['title']}' in {time_diff_minutes:.1f} minutes"
                return (False, reason, event)

            # Check if event just happened (still in blackout after)
            if -blackout_after_mins <= time_diff_minutes < 0:
                reason = f"{event['country']} {event['impact']}-impact event '{event['title']}' happened {abs(time_diff_minutes):.1f} minutes ago"
                return (False, reason, event)

        # Safe to trade
        next_event = upcoming_events[0] if upcoming_events else None
        if next_event:
            time_to_next = (next_event['time'] - now).total_seconds() / 60
            reason = f"Next event in {time_to_next:.1f} minutes: {next_event['title']}"
        else:
            reason = "No upcoming events"

        return (True, reason, next_event)

    def print_upcoming_events(self, hours_ahead: int = 24):
        """Print upcoming events in readable format"""
        events = self.get_upcoming_events(hours_ahead)

        if not events:
            print(f"No high-impact EUR/CAD events in next {hours_ahead} hours")
            return

        print(f"\n{'='*70}")
        print(f"Upcoming High-Impact EUR/CAD Events (Next {hours_ahead} hours)")
        print(f"{'='*70}")

        for event in events:
            time_str = event['time'].strftime('%Y-%m-%d %H:%M:%S')
            time_until = event['time'] - datetime.now()
            hours_until = time_until.total_seconds() / 3600

            print(f"\n[{event['country']}] {event['impact'].upper()} Impact")
            print(f"Event: {event['title']}")
            print(f"Time: {time_str} (in {hours_until:.1f} hours)")

            if event['forecast']:
                print(f"Forecast: {event['forecast']}")
            if event['previous']:
                print(f"Previous: {event['previous']}")

        print(f"\n{'='*70}\n")


class NewsAwareTrader:
    """
    Trading wrapper that checks news calendar before trading
    """

    def __init__(self):
        self.calendar = EconomicCalendar()
        self.trading_allowed = True
        self.last_check_time = None

    def check_trading_status(self) -> bool:
        """
        Check if trading is currently allowed

        Returns:
            True if safe to trade, False otherwise
        """
        is_safe, reason, next_event = self.calendar.is_safe_to_trade()

        self.last_check_time = datetime.now()
        self.trading_allowed = is_safe

        if is_safe:
            print(f"✓ TRADING ALLOWED: {reason}")
        else:
            print(f"✗ TRADING BLOCKED: {reason}")

        return is_safe

    def should_increase_stops(self) -> tuple:
        """
        Check if stop losses should be widened due to nearby news

        Returns:
            Tuple (should_widen: bool, multiplier: float)
        """
        upcoming_events = self.calendar.get_upcoming_events(hours_ahead=1)

        if not upcoming_events:
            return (False, 1.0)

        now = datetime.now()
        nearest_event = upcoming_events[0]
        time_to_event = (nearest_event['time'] - now).total_seconds() / 60

        # If high-impact event within 15-60 minutes, widen stops
        if 15 <= time_to_event <= 60:
            if nearest_event['impact'].lower() == 'high':
                return (True, 1.5)  # Widen stops by 50%
            else:
                return (True, 1.25)  # Widen stops by 25%

        return (False, 1.0)

    def get_position_size_adjustment(self) -> float:
        """
        Get position size adjustment factor based on upcoming news

        Returns:
            Multiplier for position size (0.5 = half size, 1.0 = normal)
        """
        upcoming_events = self.calendar.get_upcoming_events(hours_ahead=2)

        if not upcoming_events:
            return 1.0

        high_impact_count = sum(1 for e in upcoming_events if e['impact'].lower() == 'high')

        if high_impact_count >= 2:
            return 0.5  # Half position if multiple high-impact events
        elif high_impact_count == 1:
            return 0.75  # 75% position
        else:
            return 0.9  # 90% position for medium impact

    def wait_for_trading_window(self, check_interval: int = 60):
        """
        Wait until trading is allowed

        Args:
            check_interval: Seconds between checks
        """
        print("Waiting for safe trading window...")

        while not self.check_trading_status():
            print(f"Checking again in {check_interval} seconds...")
            time.sleep(check_interval)

        print("✓ Trading window opened!")


# Example usage and testing
if __name__ == "__main__":
    print("=== EUR/CAD News-Aware Trading System ===\n")

    # Initialize calendar
    calendar = EconomicCalendar()

    # Show upcoming events
    calendar.print_upcoming_events(hours_ahead=24)

    # Check if safe to trade
    print("\n=== Current Trading Status ===")
    is_safe, reason, next_event = calendar.is_safe_to_trade()

    if is_safe:
        print(f"✓ SAFE TO TRADE")
        print(f"Reason: {reason}")
    else:
        print(f"✗ DO NOT TRADE")
        print(f"Reason: {reason}")

    # News-aware trader example
    print("\n=== News-Aware Trader Example ===")
    trader = NewsAwareTrader()

    if trader.check_trading_status():
        # Check if should adjust risk
        should_widen, stop_multiplier = trader.should_increase_stops()
        size_adjustment = trader.get_position_size_adjustment()

        if should_widen:
            print(f"⚠ Widen stops by {(stop_multiplier - 1) * 100:.0f}%")

        if size_adjustment < 1.0:
            print(f"⚠ Reduce position size to {size_adjustment * 100:.0f}%")

        print("\n✓ Ready to trade with risk adjustments")
    else:
        print("\n✗ Trading blocked due to news")
        # trader.wait_for_trading_window()  # Uncomment to wait

    print("\n=== Integration with Trading Bot ===")
    print("""
To integrate with your trading bot:

1. Check before each trade:
   trader = NewsAwareTrader()
   if trader.check_trading_status():
       # Place trade
       pass

2. Adjust risk based on news:
   should_widen, multiplier = trader.should_increase_stops()
   size_adj = trader.get_position_size_adjustment()

   stop_loss = calculate_stop() * multiplier
   position_size = calculate_size() * size_adj

3. Monitor continuously:
   # Check every 5 minutes
   while trading:
       if not trader.check_trading_status():
           close_positions()
       time.sleep(300)
    """)
