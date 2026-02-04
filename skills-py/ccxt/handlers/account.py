"""
Account and exchange management handlers.
"""

from __future__ import annotations

from typing import Any

from ..client.ccxt_client import get_ccxt_manager
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import req_list, req_string


async def list_exchanges(args: dict[str, Any]) -> ToolResult:
  """List all configured exchanges."""
  try:
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(
        content="CCXT manager not initialized. Please complete setup first.",
        is_error=True,
      )

    exchanges = manager.list_exchanges()
    if not exchanges:
      return ToolResult(content="No exchanges configured.")

    lines = ["Configured Exchanges:"]
    for exc in exchanges:
      exc_id = exc["exchange_id"]
      exc_name = exc["exchange_name"]
      sandbox = exc.get("sandbox", False)
      sandbox_str = " [Sandbox]" if sandbox else ""
      lines.append(f"  {exc_id}: {exc_name}{sandbox_str}")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_exchanges", e, ErrorCategory.ACCOUNT)


async def get_exchange_info(args: dict[str, Any]) -> ToolResult:
  """Get information about a specific exchange."""
  try:
    exchange_id = req_string(args, "exchange_id")
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(
        content="CCXT manager not initialized.",
        is_error=True,
      )

    config = manager.get_config(exchange_id)
    if not config:
      return ToolResult(
        content=f"Exchange '{exchange_id}' not found.",
        is_error=True,
      )

    lines = [
      f"Exchange ID: {config['exchange_id']}",
      f"Exchange Name: {config['exchange_name']}",
      f"Sandbox Mode: {config.get('sandbox', False)}",
      f"API Key: {'*' * 8 if config.get('api_key') else 'Not set'}",
    ]

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_exchange_info", e, ErrorCategory.ACCOUNT)


async def test_connection(args: dict[str, Any]) -> ToolResult:
  """Test connection to an exchange."""
  try:
    exchange_id = req_string(args, "exchange_id")
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(
        content="CCXT manager not initialized.",
        is_error=True,
      )

    exchange = manager.get_exchange(exchange_id)
    if not exchange:
      return ToolResult(
        content=f"Exchange '{exchange_id}' not found.",
        is_error=True,
      )

    # Try to load markets (this tests the connection)
    try:
      await exchange.load_markets()
      return ToolResult(
        content=f"Connection to {exchange_id} successful. Loaded {len(exchange.markets)} markets."
      )
    except Exception as e:
      return ToolResult(
        content=f"Connection test failed: {e!s}",
        is_error=True,
      )
  except Exception as e:
    return log_and_format_error("test_connection", e, ErrorCategory.ACCOUNT)


async def get_available_exchanges(args: dict[str, Any]) -> ToolResult:
  """List all available CCXT exchange names."""
  try:
    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(
        content="CCXT manager not initialized.",
        is_error=True,
      )

    exchanges = manager.get_available_exchanges()
    return ToolResult(content=f"Available exchanges ({len(exchanges)}):\n" + ", ".join(exchanges))
  except Exception as e:
    return log_and_format_error("get_available_exchanges", e, ErrorCategory.ACCOUNT)


async def update_exchange_settings(args: dict[str, Any]) -> ToolResult:
  """Update settings for an existing exchange connection."""
  try:
    exchange_id = req_string(args, "exchange_id")
    settings = req_list(args, "settings")

    manager = get_ccxt_manager()
    if not manager:
      return ToolResult(
        content="CCXT manager not initialized.",
        is_error=True,
      )

    config = manager.get_config(exchange_id)
    if not config:
      return ToolResult(
        content=f"Exchange '{exchange_id}' not found.",
        is_error=True,
      )

    # Merge settings array into options
    current_options = dict(config.get("options", {}))
    for setting_obj in settings:
      if isinstance(setting_obj, dict):
        # If it's an object with "key" and "value", use that structure
        if "key" in setting_obj and "value" in setting_obj:
          current_options[setting_obj["key"]] = setting_obj["value"]
        else:
          # Otherwise merge all keys from the object
          current_options.update(setting_obj)

    # Update the exchange with new options
    exchange = manager.get_exchange(exchange_id)
    if exchange:
      # Update exchange options
      exchange.options.update(current_options)

    # Update stored config
    config["options"] = current_options
    config["settings"] = settings

    lines = [
      f"Updated settings for {exchange_id}:",
      f"  Settings applied: {len(settings)} setting object(s)",
    ]

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("update_exchange_settings", e, ErrorCategory.ACCOUNT)
