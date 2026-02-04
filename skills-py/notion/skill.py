"""
Notion SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.

Usage:
    from skills.notion.skill import skill
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dev.types.skill_types import (
  SkillDefinition,
  SkillHooks,
  SkillOptionDefinition,
  SkillTool,
)
from dev.types.skill_types import (
  ToolResult as SkillToolResult,
)

from .handlers import dispatch_tool
from .setup import on_setup_cancel, on_setup_start, on_setup_submit
from .tools import ALL_TOOLS

log = logging.getLogger("skill.notion.skill")


# ---------------------------------------------------------------------------
# Convert ToolDefinition objects → SkillTool objects
# ---------------------------------------------------------------------------


def _make_execute(tool_name: str):
  """Create an async execute function for a given tool name."""

  async def execute(args: dict[str, Any]) -> SkillToolResult:
    result = await dispatch_tool(tool_name, args)
    return SkillToolResult(content=result.content, is_error=result.is_error)

  return execute


def _convert_tools() -> list[SkillTool]:
  """Convert ToolDefinition objects to SkillTool objects with execute functions."""
  skill_tools: list[SkillTool] = []
  for tool_def in ALL_TOOLS:
    skill_tools.append(
      SkillTool(
        definition=tool_def,
        execute=_make_execute(tool_def.name),
      )
    )
  return skill_tools


# ---------------------------------------------------------------------------
# Lifecycle hooks adapted for SkillContext
# ---------------------------------------------------------------------------


async def _on_load(ctx: Any) -> None:
  """Initialize Notion client using SkillContext."""
  from .server import on_skill_load

  # Read config from data dir if it exists
  config: dict[str, Any] = {}
  try:
    raw = await ctx.read_data("config.json")
    if raw:
      config = json.loads(raw)
  except Exception:
    pass

  # Build params dict that on_skill_load expects
  params: dict[str, Any] = {
    "token": config.get("token", ""),
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
  from .client import get_client

  try:
    client = get_client()
    if client:
      # Try to get user info to verify connection
      me = await client.users.me()
      return {
        "connected": True,
        "bot_name": me.get("name", "integration"),
        "bot_id": me.get("id", ""),
      }
    return {
      "connected": False,
      "bot_name": None,
      "bot_id": None,
    }
  except Exception:
    return {
      "connected": False,
      "bot_name": None,
      "bot_id": None,
    }


# ---------------------------------------------------------------------------
# Disconnect handler
# ---------------------------------------------------------------------------


async def _on_disconnect(ctx: Any) -> None:
  """Clear Notion client and credentials."""
  from .server import on_skill_unload

  await on_skill_unload()

  try:
    await ctx.write_data("config.json", "{}")
  except Exception:
    log.warning("Failed to clear config.json on disconnect")


# ---------------------------------------------------------------------------
# Tool-category toggle options
# ---------------------------------------------------------------------------

TOOL_CATEGORY_OPTIONS = [
  SkillOptionDefinition(
    name="enable_page_tools",
    type="boolean",
    label="Pages",
    description="8 tools — create, get, update, delete, list, and search pages",
    default=True,
    group="tool_categories",
    tool_filter=[
      "notion_create_page",
      "notion_delete_page",
      "notion_get_page",
      "notion_get_page_content",
      "notion_list_all_pages",
      "notion_search",
      "notion_update_page",
      "notion_append_text",
    ],
  ),
  SkillOptionDefinition(
    name="enable_database_tools",
    type="boolean",
    label="Databases",
    description="5 tools — create, get, update, query, and list databases",
    default=True,
    group="tool_categories",
    tool_filter=[
      "notion_create_database",
      "notion_get_database",
      "notion_list_all_databases",
      "notion_query_database",
      "notion_update_database",
    ],
  ),
  SkillOptionDefinition(
    name="enable_block_tools",
    type="boolean",
    label="Blocks",
    description="5 tools — get, update, delete, append, and list block children",
    default=True,
    group="tool_categories",
    tool_filter=[
      "notion_append_blocks",
      "notion_delete_block",
      "notion_get_block",
      "notion_get_block_children",
      "notion_update_block",
    ],
  ),
  SkillOptionDefinition(
    name="enable_user_comment_tools",
    type="boolean",
    label="Users & Comments",
    description="4 tools — get user, list users, create and list comments",
    default=True,
    group="tool_categories",
    tool_filter=[
      "notion_create_comment",
      "notion_get_user",
      "notion_list_comments",
      "notion_list_users",
    ],
  ),
]


# ---------------------------------------------------------------------------
# Skill definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
  name="notion",
  description="Notion workspace integration — 22 tools for pages, databases, blocks, users, comments, and search.",
  version="1.0.0",
  has_setup=True,
  has_disconnect=True,
  tick_interval=300_000,  # 5 minutes
  tools=_convert_tools(),
  options=TOOL_CATEGORY_OPTIONS,
  hooks=SkillHooks(
    on_load=_on_load,
    on_unload=_on_unload,
    on_tick=_on_tick,
    on_status=_on_status,
    on_setup_start=on_setup_start,
    on_setup_submit=on_setup_submit,
    on_setup_cancel=on_setup_cancel,
    on_disconnect=_on_disconnect,
  ),
)
