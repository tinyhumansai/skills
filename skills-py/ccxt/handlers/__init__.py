"""
Tool handler dispatcher.
"""

from __future__ import annotations

from typing import Any

from ..helpers import ToolResult
from .account import (
  get_available_exchanges,
  get_exchange_info,
  list_exchanges,
  test_connection,
  update_exchange_settings,
)
from .market import (
  fetch_markets,
  fetch_ohlcv,
  fetch_orderbook,
  fetch_ticker,
  fetch_tickers,
  fetch_trades,
)
from .trading import (
  cancel_order,
  create_order,
  fetch_balance,
  fetch_closed_orders,
  fetch_my_trades,
  fetch_open_orders,
  fetch_order,
  fetch_orders,
)

HANDLERS: dict[str, Any] = {
  # Account
  "list_exchanges": list_exchanges,
  "get_exchange_info": get_exchange_info,
  "test_connection": test_connection,
  "get_available_exchanges": get_available_exchanges,
  "update_exchange_settings": update_exchange_settings,
  # Market
  "fetch_ticker": fetch_ticker,
  "fetch_tickers": fetch_tickers,
  "fetch_orderbook": fetch_orderbook,
  "fetch_trades": fetch_trades,
  "fetch_ohlcv": fetch_ohlcv,
  "fetch_markets": fetch_markets,
  # Trading
  "fetch_balance": fetch_balance,
  "create_order": create_order,
  "cancel_order": cancel_order,
  "fetch_order": fetch_order,
  "fetch_orders": fetch_orders,
  "fetch_open_orders": fetch_open_orders,
  "fetch_closed_orders": fetch_closed_orders,
  "fetch_my_trades": fetch_my_trades,
}


async def dispatch_tool(tool_name: str, args: dict[str, Any]) -> ToolResult:
  """Dispatch a tool call to the appropriate handler."""
  handler = HANDLERS.get(tool_name)
  if not handler:
    return ToolResult(
      content=f"Unknown tool: {tool_name}",
      is_error=True,
    )
  try:
    result: ToolResult = await handler(args)
    return result
  except Exception as e:
    return ToolResult(
      content=f"Error executing {tool_name}: {e!s}",
      is_error=True,
    )
