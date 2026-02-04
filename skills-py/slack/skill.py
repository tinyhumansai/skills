"""
Slack SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.

Usage:
    from skills.slack.skill import skill
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
from .tools import TOOL_DEFINITIONS

log = logging.getLogger("skill.slack.skill")


# ---------------------------------------------------------------------------
# Convert tool definitions → SkillTool objects
# ---------------------------------------------------------------------------


def _make_execute(tool_name: str):
  """Create an async execute function for a given tool name."""

  async def execute(args: dict[str, Any]) -> SkillToolResult:
    result = await dispatch_tool(tool_name, args)
    return SkillToolResult(content=result.content, is_error=result.is_error)

  return execute


def _build_tools() -> list[SkillTool]:
  """Build SkillTool list from tool definitions."""
  skill_tools: list[SkillTool] = []
  for name, description, schema in TOOL_DEFINITIONS:
    definition = ToolDefinition(
      name=name,
      description=description,
      parameters=schema,
    )
    skill_tools.append(
      SkillTool(
        definition=definition,
        execute=_make_execute(name),
      )
    )
  return skill_tools


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------


async def _on_load(ctx: Any) -> None:
  """Initialize Slack client using SkillContext."""
  from .client.slack_client import SlackClient, set_client
  from .state import store

  # Read config from data dir if it exists
  config: dict[str, Any] = {}
  try:
    raw = await ctx.read_data("config.json")
    if raw:
      config = json.loads(raw)
      log.info("Loaded config.json: has_token=%s", bool(config.get("bot_token")))
    else:
      log.info("config.json is empty or not found")
  except Exception as exc:
    log.warning("Failed to read config.json: %s", exc)

  bot_token = config.get("bot_token", "")
  if not bot_token:
    log.warning("No bot token configured — Slack skill not initialized")
    store.set_connection_status("disconnected")
    return

  # Initialize client
  client = SlackClient(bot_token)
  try:
    store.set_connection_status("connecting")
    await client.connect()

    is_valid = await client.validate_token()
    if not is_valid:
      store.set_connection_error("Invalid bot token")
      await client.close()
      return

    # Get workspace info
    auth_result = await client.auth_test()
    store.set_workspace_info(
      auth_result.get("team", ""),
      auth_result.get("team_id", ""),
    )

    from .state.store import SlackUser

    store.set_current_user(
      SlackUser(
        id=auth_result.get("user_id", ""),
        name=auth_result.get("user", ""),
        team_id=auth_result.get("team_id", ""),
      )
    )

    set_client(client)
    store.set_connection_status("connected")
    store.set_is_initialized(True)

    log.info("Slack skill loaded successfully")
  except Exception as exc:
    log.exception("Failed to connect to Slack")
    store.set_connection_error(str(exc))
    await client.close()
    return


async def _on_unload(ctx: Any) -> None:
  """Clean up resources."""
  from .client.slack_client import get_client, set_client
  from .state import store

  try:
    client = get_client()
    if client:
      await client.close()
    set_client(None)
  except Exception:
    pass

  store.reset_state()
  log.info("Slack skill unloaded")


async def _on_tick(ctx: Any) -> None:
  """Periodic sync — refresh workspace info, check connection."""
  from .client.slack_client import get_client
  from .state import store

  state = store.get_state()
  if state.connection_status != "connected":
    return

  client = get_client()
  if not client:
    return

  # Refresh workspace info periodically
  try:
    auth_result = await client.auth_test()
    store.set_workspace_info(
      auth_result.get("team", ""),
      auth_result.get("team_id", ""),
    )
  except Exception:
    log.debug("Failed to refresh workspace info on tick", exc_info=True)


async def _on_status(ctx: Any) -> dict[str, Any]:
  """Return current skill status information."""
  from .state import store

  state = store.get_state()
  return {
    "connection_status": state.connection_status,
    "is_initialized": state.is_initialized,
    "connection_error": state.connection_error,
    "current_user": state.current_user.model_dump() if state.current_user else None,
    "workspace_name": state.workspace_name,
    "workspace_id": state.workspace_id,
  }


# ---------------------------------------------------------------------------
# Disconnect handler
# ---------------------------------------------------------------------------


async def _on_disconnect(ctx: Any) -> None:
  """Close Slack client and clear credentials."""
  from .client.slack_client import get_client, set_client
  from .state import store

  # Disconnect the client
  try:
    client = get_client()
    if client:
      await client.close()
    set_client(None)
  except Exception:
    pass

  store.reset_state()

  # Clear persisted config
  try:
    await ctx.write_data("config.json", "{}")
  except Exception:
    log.warning("Failed to clear config.json on disconnect")


# ---------------------------------------------------------------------------
# Tool-category toggle options
# ---------------------------------------------------------------------------

TOOL_CATEGORY_OPTIONS = [
  SkillOptionDefinition(
    name="enable_channel_tools",
    type="boolean",
    label="Channel Management",
    description="11 tools — list, create, join, leave, archive channels, set topic/purpose",
    default=True,
    group="tool_categories",
    tool_filter=[
      "list_channels",
      "get_channel",
      "create_channel",
      "join_channel",
      "leave_channel",
      "archive_channel",
      "unarchive_channel",
      "set_channel_topic",
      "set_channel_purpose",
      "get_channel_members",
    ],
  ),
  SkillOptionDefinition(
    name="enable_message_tools",
    type="boolean",
    label="Messaging",
    description="5 tools — send, get, edit, delete messages, get permalinks",
    default=True,
    group="tool_categories",
    tool_filter=[
      "send_message",
      "get_messages",
      "edit_message",
      "delete_message",
      "get_message_permalink",
    ],
  ),
  SkillOptionDefinition(
    name="enable_user_tools",
    type="boolean",
    label="Users & DMs",
    description="5 tools — list users, get user info, lookup by email, open/list DMs",
    default=True,
    group="tool_categories",
    tool_filter=[
      "list_users",
      "get_user",
      "get_user_by_email",
      "open_dm",
      "list_dms",
    ],
  ),
  SkillOptionDefinition(
    name="enable_search_tools",
    type="boolean",
    label="Search",
    description="2 tools — search messages and files",
    default=True,
    group="tool_categories",
    tool_filter=[
      "search_messages",
      "search_all",
    ],
  ),
]


# ---------------------------------------------------------------------------
# Skill definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
  name="slack",
  description="Slack workspace integration — send messages, manage channels, search conversations, and interact with Slack workspaces.",
  version="1.0.0",
  has_setup=True,
  has_disconnect=True,
  tick_interval=300_000,  # 5 minutes
  tools=_build_tools(),
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
