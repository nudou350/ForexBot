"""Risk management module for EUR/CAD trading bot"""

from .risk_manager import RiskManager
from .emergency_stop import EmergencyStopSystem

__all__ = ['RiskManager', 'EmergencyStopSystem']
