"""
Email SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.

Usage:
    from skills.email.skill import skill
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
  ToolDefinition,
)
from dev.types.skill_types import (
  ToolResult as SkillToolResult,
)

from .handlers import dispatch_tool
from .setup import on_setup_cancel, on_setup_start, on_setup_submit
from .tools import ALL_TOOLS

log = logging.getLogger("skill.email.skill")


# ---------------------------------------------------------------------------
# Convert MCP Tool objects -> SkillTool objects
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
  """Initialize IMAP + SMTP + SQLite using SkillContext."""
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
  from .state.store import get_state

  state = get_state()
  return {
    "connection_status": state.connection_status,
    "is_initialized": state.is_initialized,
    "connection_error": state.connection_error,
    "account": state.account.model_dump() if state.account else None,
    "is_syncing": state.is_syncing,
    "last_sync": state.last_sync,
    "total_unread": state.total_unread,
  }


# ---------------------------------------------------------------------------
# Disconnect handler
# ---------------------------------------------------------------------------


async def _on_disconnect(ctx: Any) -> None:
  """Close IMAP/SMTP connections and clear credentials."""
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
    name="enable_folder_tools",
    type="boolean",
    label="Folder Management",
    description="5 tools — create, rename, delete, list, and get folder status",
    default=True,
    group="tool_categories",
    tool_filter=[
      "create_folder",
      "delete_folder",
      "get_folder_status",
      "list_folders",
      "rename_folder",
    ],
  ),
  SkillOptionDefinition(
    name="enable_read_tools",
    type="boolean",
    label="Message Reading",
    description="7 tools — get messages, threads, unread counts, and mailbox summaries",
    default=True,
    group="tool_categories",
    tool_filter=[
      "count_messages",
      "get_mailbox_summary",
      "get_message",
      "get_recent_messages",
      "get_thread",
      "get_unread_count",
      "get_unread_messages",
    ],
  ),
  SkillOptionDefinition(
    name="enable_send_tools",
    type="boolean",
    label="Sending & Replying",
    description="3 tools — send email, reply to email, forward email",
    default=True,
    group="tool_categories",
    tool_filter=[
      "forward_email",
      "reply_to_email",
      "send_email",
    ],
  ),
  SkillOptionDefinition(
    name="enable_manage_tools",
    type="boolean",
    label="Message Management",
    description="7 tools — archive, delete, move, flag/unflag, mark read/unread",
    default=True,
    group="tool_categories",
    tool_filter=[
      "archive_message",
      "delete_message",
      "flag_message",
      "mark_read",
      "mark_unread",
      "move_message",
      "unflag_message",
    ],
  ),
  SkillOptionDefinition(
    name="enable_attachment_tools",
    type="boolean",
    label="Attachments",
    description="3 tools — list, get info, and save attachments",
    default=True,
    group="tool_categories",
    tool_filter=[
      "get_attachment_info",
      "list_attachments",
      "save_attachment",
    ],
  ),
  SkillOptionDefinition(
    name="enable_draft_tools",
    type="boolean",
    label="Drafts",
    description="4 tools — save, update, delete, and list drafts",
    default=True,
    group="tool_categories",
    tool_filter=[
      "delete_draft",
      "list_drafts",
      "save_draft",
      "update_draft",
    ],
  ),
  SkillOptionDefinition(
    name="enable_account_tools",
    type="boolean",
    label="Account & Sync",
    description="6 tools — account info, connection test, sync status, search messages/contacts",
    default=True,
    group="tool_categories",
    tool_filter=[
      "get_account_info",
      "get_sync_status",
      "list_messages",
      "search_contacts",
      "search_messages",
      "test_connection",
    ],
  ),
]


# ---------------------------------------------------------------------------
# Skill definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
  name="email",
  description="Email integration via IMAP/SMTP — 35 tools for reading, sending, searching, and managing email across Gmail, Outlook, Yahoo, iCloud, and custom servers.",
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
