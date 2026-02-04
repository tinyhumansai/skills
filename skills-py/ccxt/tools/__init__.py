"""
CCXT tool definitions organized by domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .account import account_tools
from .market import market_tools
from .trading import trading_tools

if TYPE_CHECKING:
  from mcp.types import Tool

ALL_TOOLS: list[Tool] = [
  *account_tools,
  *market_tools,
  *trading_tools,
]
