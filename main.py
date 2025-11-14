"""
EUR/CAD Trading Bot - Main Entry Point
Run this file to start the trading bot
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

from src.bot import main

if __name__ == "__main__":
    main()
