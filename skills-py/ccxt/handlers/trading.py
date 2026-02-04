"""
Trading handlers (orders, balance, positions).
"""

from __future__ import annotations

from typing import Any

from ..client.ccxt_client import get_ccxt_manager
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import opt_list, opt_number, opt_string, req_string


async def fetch_balance(args: dict[str, Any]) -> ToolResult:
  """Fetch account balance."""
  try:
    exchange_id = req_string(args, "exchange_id")
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    balance = await exchange.fetch_balance()
    lines = [f"Balance for {exchange_id}:"]

    # Show non-zero balances
    for currency, amounts in balance.items():
      if currency in ["info", "free", "used", "total"]:
        continue
      if isinstance(amounts, dict):
        free = amounts.get("free", 0)
        used = amounts.get("used", 0)
        total = amounts.get("total", 0)
        if total > 0:
          lines.append(f"  {currency}: Free={free}, Used={used}, Total={total}")

    if len(lines) == 1:
      lines.append("  No balances found")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_balance", e, ErrorCategory.TRADING)


async def create_order(args: dict[str, Any]) -> ToolResult:
  """Create a new order."""
  try:
    exchange_id = req_string(args, "exchange_id")
    symbol = req_string(args, "symbol")
    side = req_string(args, "side")
    order_type = req_string(args, "type")
    amount = float(req_string(args, "amount"))

    if side not in ["buy", "sell"]:
      return ToolResult(content="Side must be 'buy' or 'sell'", is_error=True)

    if order_type not in ["market", "limit"]:
      return ToolResult(content="Type must be 'market' or 'limit'", is_error=True)

    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    order_params: dict[str, Any] = {
      "symbol": symbol,
      "type": order_type,
      "side": side,
      "amount": amount,
    }

    if order_type == "limit":
      price = float(req_string(args, "price"))
      order_params["price"] = price

    # Process settings array if provided
    settings = opt_list(args, "settings")
    if settings:
      for setting_obj in settings:
        if isinstance(setting_obj, dict):
          # If it's an object with "key" and "value", use that structure
          if "key" in setting_obj and "value" in setting_obj:
            order_params[setting_obj["key"]] = setting_obj["value"]
          else:
            # Otherwise merge all keys from the object
            order_params.update(setting_obj)

    order = await exchange.create_order(**order_params)
    lines = [
      f"Order created on {exchange_id}:",
      f"  Order ID: {order.get('id', 'N/A')}",
      f"  Symbol: {order.get('symbol', symbol)}",
      f"  Side: {order.get('side', side)}",
      f"  Type: {order.get('type', order_type)}",
      f"  Amount: {order.get('amount', amount)}",
      f"  Price: {order.get('price', 'N/A')}",
      f"  Status: {order.get('status', 'N/A')}",
    ]

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("create_order", e, ErrorCategory.TRADING)


async def cancel_order(args: dict[str, Any]) -> ToolResult:
  """Cancel an order."""
  try:
    exchange_id = req_string(args, "exchange_id")
    order_id = req_string(args, "order_id")
    symbol = req_string(args, "symbol")
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    await exchange.cancel_order(order_id, symbol)
    return ToolResult(content=f"Order {order_id} cancelled successfully.")
  except Exception as e:
    return log_and_format_error("cancel_order", e, ErrorCategory.TRADING)


async def fetch_order(args: dict[str, Any]) -> ToolResult:
  """Fetch order details."""
  try:
    exchange_id = req_string(args, "exchange_id")
    order_id = req_string(args, "order_id")
    symbol = req_string(args, "symbol")
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    order = await exchange.fetch_order(order_id, symbol)
    lines = [
      f"Order {order_id} on {exchange_id}:",
      f"  Symbol: {order.get('symbol', symbol)}",
      f"  Side: {order.get('side', 'N/A')}",
      f"  Type: {order.get('type', 'N/A')}",
      f"  Amount: {order.get('amount', 'N/A')}",
      f"  Price: {order.get('price', 'N/A')}",
      f"  Status: {order.get('status', 'N/A')}",
      f"  Filled: {order.get('filled', 'N/A')}",
    ]

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_order", e, ErrorCategory.TRADING)


async def fetch_orders(args: dict[str, Any]) -> ToolResult:
  """Fetch all orders."""
  try:
    exchange_id = req_string(args, "exchange_id")
    symbol = opt_string(args, "symbol")
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    if symbol:
      orders = await exchange.fetch_orders(symbol)
    else:
      orders = await exchange.fetch_orders()

    lines = [f"Orders on {exchange_id}:"]
    for order in orders[:20]:  # Limit display
      lines.append(
        f"  {order.get('id', 'N/A')}: {order.get('symbol', 'N/A')} "
        f"{order.get('side', 'N/A')} {order.get('amount', 'N/A')} @ "
        f"{order.get('price', 'N/A')} [{order.get('status', 'N/A')}]"
      )

    if len(orders) > 20:
      lines.append(f"\n... and {len(orders) - 20} more")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_orders", e, ErrorCategory.TRADING)


async def fetch_open_orders(args: dict[str, Any]) -> ToolResult:
  """Fetch open orders."""
  try:
    exchange_id = req_string(args, "exchange_id")
    symbol = opt_string(args, "symbol")
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    if symbol:
      orders = await exchange.fetch_open_orders(symbol)
    else:
      orders = await exchange.fetch_open_orders()

    lines = [f"Open orders on {exchange_id}:"]
    for order in orders[:20]:
      lines.append(
        f"  {order.get('id', 'N/A')}: {order.get('symbol', 'N/A')} "
        f"{order.get('side', 'N/A')} {order.get('amount', 'N/A')} @ "
        f"{order.get('price', 'N/A')}"
      )

    if not orders:
      lines.append("  No open orders")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_open_orders", e, ErrorCategory.TRADING)


async def fetch_closed_orders(args: dict[str, Any]) -> ToolResult:
  """Fetch closed orders."""
  try:
    exchange_id = req_string(args, "exchange_id")
    symbol = opt_string(args, "symbol")
    limit = opt_number(args, "limit", 50)
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    if symbol:
      orders = await exchange.fetch_closed_orders(symbol, limit=limit)
    else:
      orders = await exchange.fetch_closed_orders(limit=limit)

    lines = [f"Closed orders on {exchange_id}:"]
    for order in orders[:20]:
      lines.append(
        f"  {order.get('id', 'N/A')}: {order.get('symbol', 'N/A')} "
        f"{order.get('side', 'N/A')} {order.get('amount', 'N/A')} @ "
        f"{order.get('price', 'N/A')} [{order.get('status', 'N/A')}]"
      )

    if not orders:
      lines.append("  No closed orders")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_closed_orders", e, ErrorCategory.TRADING)


async def fetch_my_trades(args: dict[str, Any]) -> ToolResult:
  """Fetch trade history."""
  try:
    exchange_id = req_string(args, "exchange_id")
    symbol = opt_string(args, "symbol")
    limit = opt_number(args, "limit", 50)
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(content="CCXT manager not initialized.", is_error=True)

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(content=f"Exchange '{exchange_id}' not found.", is_error=True)

    if symbol:
      trades = await exchange.fetch_my_trades(symbol, limit=limit)
    else:
      trades = await exchange.fetch_my_trades(limit=limit)

    lines = [f"Trade history on {exchange_id}:"]
    for trade in trades[:20]:
      lines.append(
        f"  {trade.get('id', 'N/A')}: {trade.get('symbol', 'N/A')} "
        f"{trade.get('side', 'N/A')} {trade.get('amount', 'N/A')} @ "
        f"{trade.get('price', 'N/A')} (Fee: {trade.get('fee', {}).get('cost', 'N/A')})"
      )

    if not trades:
      lines.append("  No trades found")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("fetch_my_trades", e, ErrorCategory.TRADING)
