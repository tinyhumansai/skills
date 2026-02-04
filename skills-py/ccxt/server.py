"""
MCP server + skill lifecycle hooks.

Uses the official `mcp` Python SDK. Handles tools/list, tools/call,
and skill lifecycle methods (load, unload, tick).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from .client.ccxt_client import create_ccxt_manager, set_ccxt_manager
from .handlers import dispatch_tool
from .tools import ALL_TOOLS

log = logging.getLogger("skill.ccxt.server")


def create_mcp_server() -> Server:
  """Create and configure the MCP server with all tool handlers."""
  server = Server("ccxt-skill")

  @server.list_tools()
  async def list_tools() -> list[Tool]:
    return ALL_TOOLS

  @server.call_tool()
  async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    args = arguments or {}
    result = await dispatch_tool(name, args)
    return [TextContent(type="text", text=result.content)]

  return server


async def on_skill_load(
  params: dict[str, Any],
  set_state_fn: Any = None,
) -> None:
  """Called when the host loads this skill. Initializes CCXT manager with configured exchanges."""
  params.get("dataDir", "data")

  # Read config
  config: dict[str, Any] = params.get("config", {})

  if not config:
    log.warning("No config found — skill needs setup")
    return

  exchanges_config = config.get("exchanges", [])
  if not exchanges_config:
    log.warning("No exchanges configured")
    return

  # Create CCXT manager
  manager = create_ccxt_manager()
  set_ccxt_manager(manager)

  # Add all configured exchanges
  for exc_config in exchanges_config:
    exchange_id = exc_config.get("exchange_id")
    exchange_name = exc_config.get("exchange_name")
    api_key = exc_config.get("api_key", "")
    secret = exc_config.get("secret", "")
    password = exc_config.get("password", "")
    sandbox = exc_config.get("sandbox", False)
    options = exc_config.get("options", {})
    settings = exc_config.get("settings")

    if not exchange_id or not exchange_name:
      log.warning("Skipping invalid exchange config: missing exchange_id or exchange_name")
      continue

    # Convert settings JSON string to array if present
    settings_array = None
    if settings:
      if isinstance(settings, str):
        try:
          settings_data = json.loads(settings)
          if isinstance(settings_data, list):
            settings_array = settings_data
          elif isinstance(settings_data, dict):
            # Convert single object to array format
            settings_array = [settings_data]
        except json.JSONDecodeError:
          log.warning("Invalid settings JSON for exchange %s", exchange_id)
      elif isinstance(settings, list):
        settings_array = settings

    success = manager.add_exchange(
      exchange_id=exchange_id,
      exchange_name=exchange_name,
      api_key=api_key,
      secret=secret,
      password=password,
      sandbox=sandbox,
      options=options,
      settings=settings_array,
    )

    if success:
      log.info("Loaded exchange: %s (%s)", exchange_id, exchange_name)
    else:
      log.error("Failed to load exchange: %s (%s)", exchange_id, exchange_name)


async def on_skill_unload() -> None:
  """Called when the skill is unloaded. Clean up connections."""
  from .client.ccxt_client import get_ccxt_manager

  manager = get_ccxt_manager()
  if manager:
    # CCXT exchanges don't need explicit cleanup, but we can clear the manager
    log.info("Unloading CCXT skill")


async def on_skill_tick() -> None:
  """Periodic tick handler. Can be used for health checks or background tasks."""
  # Optional: implement health checks or background sync
  pass
