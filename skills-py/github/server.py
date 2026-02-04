"""
MCP server + skill lifecycle hooks.

Handles tools/list, tools/call, and skill lifecycle (load, unload, tick).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client.gh_client import create_client, get_client
from .handlers import dispatch_tool
from .tools import ALL_TOOLS

log = logging.getLogger("skill.github.server")


def create_mcp_server() -> Server:
  """Create and configure the MCP server with all tool handlers."""
  server = Server("github-skill")

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
  """Called when the host loads this skill. Initializes PyGithub client."""
  token = os.environ.get("GITHUB_TOKEN", params.get("token", ""))

  if not token:
    log.error("No GitHub token available — skill will not be functional")
    return

  # Initialize client
  client = create_client()
  await client.initialize(token)

  # Verify auth
  authed = await client.check_auth()
  if authed:
    log.info("GitHub skill loaded — authenticated as %s", client.username)
  else:
    log.error("GitHub authentication failed")

  # Sync state to host if available
  if set_state_fn:
    set_state_fn(
      {
        "authenticated": authed,
        "username": client.username if authed else "",
      }
    )


async def on_skill_unload() -> None:
  """Called when the host unloads this skill."""
  try:
    client = get_client()
    await client.close()
  except Exception:
    log.exception("Error closing GitHub client")
  log.info("GitHub skill unloaded")


async def on_skill_tick() -> None:
  """Called periodically (every 5 minutes). Check notifications count."""
  try:
    client = get_client()
    if not client.is_authed:
      return
    from .client.gh_client import run_sync

    user = await run_sync(client.gh.get_user)
    notifications = await run_sync(user.get_notifications)
    count = await run_sync(lambda: notifications.totalCount)
    if count > 0:
      log.info("GitHub: %d unread notifications", count)
  except Exception:
    log.debug("Tick: could not check notifications", exc_info=True)


async def run_server() -> None:
  """Run the MCP server on stdio."""
  server = create_mcp_server()
  async with stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, server.create_initialization_options())
