"""
CCXT SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.

Usage:
    from skills.ccxt.skill import skill
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dev.types.skill_types import (
  SkillDefinition,
  SkillHooks,
  SkillTool,
  ToolDefinition,
)
from dev.types.skill_types import (
  ToolResult as SkillToolResult,
)

from .handlers import dispatch_tool
from .setup import on_setup_cancel, on_setup_start, on_setup_submit
from .tools import ALL_TOOLS

log = logging.getLogger("skill.ccxt.skill")


# ---------------------------------------------------------------------------
# Convert MCP Tool objects → SkillTool objects
# ---------------------------------------------------------------------------


def _make_execute(tool_name: str):
  """Create an async execute function for a given tool name."""

  async def execute(args: dict[str, Any]) -> SkillToolResult:
    result = await dispatch_tool(tool_name, args)
    return SkillToolResult(content=result.content, is_error=result.is_error)

  return execute


def _convert_tools() -> list[SkillTool]:
  """Convert MCP Tool definitions to SkillTool objects."""
  skill_tools: list[SkillTool] = []
  for mcp_tool in ALL_TOOLS:
    schema = mcp_tool.inputSchema if isinstance(mcp_tool.inputSchema, dict) else {}
    definition = ToolDefinition(
      name=mcp_tool.name,
      description=mcp_tool.description or "",
      parameters=schema,
    )
    skill_tools.append(
      SkillTool(
        definition=definition,
        execute=_make_execute(mcp_tool.name),
      )
    )
  return skill_tools


# ---------------------------------------------------------------------------
# Lifecycle hooks adapted for SkillContext
# ---------------------------------------------------------------------------


async def _on_load(ctx: Any) -> None:
  """Initialize CCXT manager using SkillContext."""
  from .server import on_skill_load

  # Read config from data dir if it exists
  config: dict[str, Any] = {}
  try:
    raw = await ctx.read_data("config.json")
    if raw:
      config = json.loads(raw)
      log.info("Loaded config.json: exchanges=%s", len(config.get("exchanges", [])))
    else:
      log.info("config.json is empty or not found")
  except Exception as exc:
    log.warning("Failed to read config.json: %s", exc)

  # Build params dict that on_skill_load expects
  params: dict[str, Any] = {
    "dataDir": ctx.data_dir,
    "config": config,
  }

  # Pass set_state as a callback for host sync
  def set_state_fn(partial: dict[str, Any]) -> None:
    ctx.set_state(partial)

  await on_skill_load(params, set_state_fn=set_state_fn)


async def _on_unload(ctx: Any) -> None:
  from .server import on_skill_unload

  await on_skill_unload()


async def _on_tick(ctx: Any) -> None:
  from .server import on_skill_tick

  await on_skill_tick()


async def _on_status(ctx: Any) -> dict[str, Any]:
  """Return current skill status information."""
  from .client.ccxt_client import get_ccxt_manager

  manager = get_ccxt_manager()
  if not manager:
    return {
      "initialized": False,
      "exchange_count": 0,
    }

  exchanges = manager.list_exchanges()
  return {
    "initialized": True,
    "exchange_count": len(exchanges),
    "exchanges": exchanges,
  }


# ---------------------------------------------------------------------------
# Disconnect handler
# ---------------------------------------------------------------------------


async def _on_disconnect(ctx: Any) -> None:
  """Clear exchange connections and config."""
  from .server import on_skill_unload

  await on_skill_unload()

  try:
    await ctx.write_data("config.json", "{}")
  except Exception:
    log.warning("Failed to clear config.json on disconnect")


# ---------------------------------------------------------------------------
# Skill definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
  name="ccxt",
  description="Cryptocurrency exchange trading connector via CCXT — connect to multiple exchanges simultaneously for trading, balance checks, market data, and order management.",
  version="1.0.0",
  hooks=SkillHooks(
    on_load=_on_load,
    on_unload=_on_unload,
    on_tick=_on_tick,
    on_status=_on_status,
    on_disconnect=_on_disconnect,
    on_setup_start=on_setup_start,
    on_setup_submit=on_setup_submit,
    on_setup_cancel=on_setup_cancel,
  ),
  tools=_convert_tools(),
)
