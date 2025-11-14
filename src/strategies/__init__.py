"""Trading strategies module for EUR/CAD bot"""

from .mean_reversion import MeanReversionStrategy
from .trend_following import TrendFollowingStrategy
from .grid_trading import GridTradingStrategy

__all__ = [
    'MeanReversionStrategy',
    'TrendFollowingStrategy',
    'GridTradingStrategy'
]
