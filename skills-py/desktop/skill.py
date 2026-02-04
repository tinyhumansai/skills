"""
Desktop SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from dev.types.skill_types import (
  SkillDefinition,
  SkillHooks,
  SkillTool,
  ToolDefinition,
)
from dev.types.skill_types import (
  ToolResult as SkillToolResult,
)

from .handlers.desktop_handlers import dispatch_tool, set_desktop_client
from .tools import ALL_TOOLS

if TYPE_CHECKING:
  from .client.desktop_client import DesktopClient
else:
  try:
    from .client.desktop_client import DesktopClient
  except ImportError:
    DesktopClient = None  # type: ignore[assignment, misc]

log = logging.getLogger("skill.desktop.skill")


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


_desktop_client: DesktopClient | None = None


async def _on_load(ctx: Any) -> None:
  """Initialize desktop client."""
  global _desktop_client

  if DesktopClient is None:
    log.error("DesktopClient not available: pynput is not installed")
    _desktop_client = None
    return

  # DesktopClient is not None here due to the check above
  try:
    _desktop_client = DesktopClient()  # type: ignore[call-arg]
    set_desktop_client(_desktop_client)
    log.info("Desktop client initialized")
  except Exception as exc:
    log.error("Failed to initialize desktop client: %s", exc)
    _desktop_client = None


async def _on_unload(ctx: Any) -> None:
  """Clean up on unload."""
  global _desktop_client

  _desktop_client = None
  set_desktop_client(None)
  log.info("Desktop skill unloaded")


async def _on_status(ctx: Any) -> dict[str, Any]:
  """Return current skill status."""
  global _desktop_client

  if not _desktop_client:
    return {
      "status": "not_initialized",
      "message": "Desktop client not initialized",
    }

  try:
    screen_info = _desktop_client.screen_size()
    mouse_pos = _desktop_client.mouse_position()

    return {
      "status": "ready",
      "screen": screen_info if screen_info.get("success") else None,
      "mouse_position": mouse_pos if mouse_pos.get("success") else None,
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
  name="desktop",
  description="Desktop automation skill — control mouse and keyboard to autonomously navigate and interact with the desktop, applications, and windows. Supports mouse movement, clicking, scrolling, keyboard typing, hotkeys, and screen capture.",
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
