"""
CCXT tool definitions organized by domain.
"""

from __future__ import annotations

from mcp.types import Tool

from .account import account_tools
from .market import market_tools
from .trading import trading_tools

ALL_TOOLS: list[Tool] = [
  *account_tools,
  *market_tools,
  *trading_tools,
]
