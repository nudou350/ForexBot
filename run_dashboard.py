"""
EUR/CAD Trading Bot Dashboard Launcher
Run this to view bot performance in real-time
"""

import sys
import os
import asyncio

# Fix for Python 3.14 event loop compatibility
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Add src directory to path
sys.path.append(os.path.dirname(__file__))

from src.dashboard.dashboard import main

if __name__ == "__main__":
    print("""
    =========================================
       EUR/CAD BOT DASHBOARD
    =========================================
       Starting web dashboard...

       Make sure the bot is running first!
       (Run: python main.py)

       Then open your browser to:
       http://localhost:8050
    =========================================
    """)

    main()
