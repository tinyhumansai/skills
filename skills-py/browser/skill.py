"""
Browser SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.
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

from .client.browser_client import BrowserClient
from .handlers.browser_handlers import dispatch_tool, set_browser_client
from .tools import ALL_TOOLS

log = logging.getLogger("skill.browser.skill")


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
# Lifecycle hooks
# ---------------------------------------------------------------------------


_browser_client: BrowserClient | None = None


async def _on_load(ctx: Any) -> None:
  """Initialize browser client from config."""
  global _browser_client

  # Read config from data dir if it exists
  config: dict[str, Any] = {}
  headless = True
  browser_type = "chromium"

  try:
    raw = await ctx.read_data("config.json")
    if raw:
      config = json.loads(raw)
      headless = config.get("headless", True)
      browser_type = config.get("browser_type", "chromium")
      log.info(
        "Loaded config.json: headless=%s, browser_type=%s",
        headless,
        browser_type,
      )
  except Exception as exc:
    log.info("No config.json found, using defaults: %s", exc)

  # Initialize browser client
  try:
    _browser_client = BrowserClient(headless=headless, browser_type=browser_type)
    await _browser_client.start()
    set_browser_client(_browser_client)
    log.info(
      "Browser client initialized: %s (headless=%s)",
      browser_type,
      headless,
    )
  except Exception as exc:
    log.error("Failed to initialize browser client: %s", exc)
    _browser_client = None


async def _on_unload(ctx: Any) -> None:
  """Clean up on unload."""
  global _browser_client

  if _browser_client:
    try:
      await _browser_client.stop()
    except Exception as exc:
      log.error("Error stopping browser: %s", exc)
    _browser_client = None
    set_browser_client(None)

  log.info("Browser skill unloaded")


async def _on_status(ctx: Any) -> dict[str, Any]:
  """Return current skill status."""
  global _browser_client

  if not _browser_client:
    return {
      "status": "not_initialized",
      "message": "Browser not initialized",
    }

  try:
    pages_info = await _browser_client.get_pages()
    return {
      "status": "ready",
      "browser_type": _browser_client.browser_type,
      "headless": _browser_client.headless,
      "pages": pages_info.get("pages", []),
      "current_page_index": pages_info.get("current_index", 0),
    }
  except Exception as exc:
    return {
      "status": "error",
      "message": f"Error getting status: {exc}",
    }


# ---------------------------------------------------------------------------
# Skill Definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
  name="browser",
  description="Browser automation and control skill — navigate pages, interact with elements, execute JavaScript, intercept network requests, manage cookies, take screenshots, and automate web workflows using Playwright.",
  version="1.0.0",
  hooks=SkillHooks(
    on_load=_on_load,
    on_unload=_on_unload,
    on_status=_on_status,
  ),
  tools=_convert_tools(),
  has_setup=False,
  has_disconnect=False,
)
