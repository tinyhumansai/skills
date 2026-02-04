"""
Telegram SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.

Usage:
    from skills.telegram.skill import skill
"""

from __future__ import annotations

import json
import logging
import os
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
from dev.types.trigger_types import (
  TriggerFieldSchema,
  TriggerSchema,
  TriggerTypeDefinition,
)

from .handlers import dispatch_tool
from .setup import on_setup_cancel, on_setup_start, on_setup_submit
from .tools import ALL_TOOLS

log = logging.getLogger("skill.telegram.skill")


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
  """Initialize Telethon + SQLite using SkillContext."""
  from .server import on_skill_load

  # Read config from data dir if it exists
  config: dict[str, Any] = {}
  try:
    raw = await ctx.read_data("config.json")
    if raw:
      config = json.loads(raw)
      log.info(
        "Loaded config.json: keys=%s, has_session=%s",
        list(config.keys()),
        bool(config.get("session_string")),
      )
    else:
      log.info("config.json is empty or not found")
  except Exception as exc:
    log.warning("Failed to read config.json: %s", exc)

  # Build params dict that on_skill_load expects
  params: dict[str, Any] = {
    "dataDir": ctx.data_dir,
    "sessionString": config.get("session_string", ""),
    "apiId": config.get("api_id", os.environ.get("TELEGRAM_API_ID", "")),
    "apiHash": config.get("api_hash", os.environ.get("TELEGRAM_API_HASH", "")),
  }

  # Pass set_state as an async callback for host sync.
  # sync.py awaits this callback, so it must be a coroutine.
  async def set_state_fn(partial: dict[str, Any]) -> None:
    ctx.set_state(partial)

  # Extract server-level callbacks if available (SkillServer runtime)
  upsert_entity_fn = getattr(ctx, "_upsert_entity", None)
  upsert_relationship_fn = getattr(ctx, "_upsert_relationship", None)
  request_summarization_fn = getattr(ctx, "_request_summarization", None)
  fire_trigger_fn = getattr(ctx, "_fire_trigger", None)

  await on_skill_load(
    params,
    set_state_fn=set_state_fn,
    upsert_entity_fn=upsert_entity_fn,
    upsert_relationship_fn=upsert_relationship_fn,
    request_summarization_fn=request_summarization_fn,
    fire_trigger_fn=fire_trigger_fn,
  )


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
    "auth_status": state.auth_status,
    "is_initialized": state.is_initialized,
    "connection_error": state.connection_error,
    "auth_error": state.auth_error,
    "current_user": state.current_user.model_dump() if state.current_user else None,
  }


# ---------------------------------------------------------------------------
# Disconnect handler
# ---------------------------------------------------------------------------


async def _on_disconnect(ctx: Any) -> None:
  """Disconnect Telethon client and clear credentials."""
  from .server import on_skill_unload

  # Disconnect the client
  await on_skill_unload()

  # Clear persisted config (session, api credentials)
  try:
    await ctx.write_data("config.json", "{}")
  except Exception:
    log.warning("Failed to clear config.json on disconnect")


# ---------------------------------------------------------------------------
# Trigger schema — declares what trigger types this skill supports
# ---------------------------------------------------------------------------

TELEGRAM_TRIGGER_SCHEMA = TriggerSchema(
  trigger_types=[
    TriggerTypeDefinition(
      type="message_match",
      label="Message Match",
      description="Fires when an incoming message matches the specified conditions",
      condition_fields=[
        TriggerFieldSchema(name="message.text", type="string", description="Message text content"),
        TriggerFieldSchema(
          name="message.sender_name", type="string", description="Sender's display name"
        ),
        TriggerFieldSchema(name="message.chat_name", type="string", description="Chat/group title"),
        TriggerFieldSchema(name="message.chat_id", type="string", description="Chat ID"),
        TriggerFieldSchema(name="message.sender_id", type="string", description="Sender's user ID"),
        TriggerFieldSchema(
          name="message.is_outgoing", type="boolean", description="Whether the message is outgoing"
        ),
      ],
      config_schema={
        "type": "object",
        "properties": {
          "chat_filter": {
            "type": "string",
            "description": "Only match messages from chats whose name contains this string",
          },
          "sender_filter": {
            "type": "string",
            "description": "Only match messages from senders whose name contains this string",
          },
          "exclude_outgoing": {
            "type": "boolean",
            "description": "Skip outgoing messages (default: true)",
            "default": True,
          },
        },
      },
    ),
    TriggerTypeDefinition(
      type="chat_event",
      label="Chat Event",
      description="Fires on chat membership changes (user joined, left, kicked, etc.)",
      condition_fields=[
        TriggerFieldSchema(
          name="event.action",
          type="string",
          description="Action type: user_joined, user_left, user_added, user_kicked",
        ),
        TriggerFieldSchema(name="event.chat_name", type="string", description="Chat/group title"),
        TriggerFieldSchema(name="event.chat_id", type="string", description="Chat ID"),
      ],
      config_schema={
        "type": "object",
        "properties": {
          "chat_filter": {
            "type": "string",
            "description": "Only match events from chats whose name contains this string",
          },
        },
      },
    ),
  ]
)


# ---------------------------------------------------------------------------
# Trigger hooks
# ---------------------------------------------------------------------------


async def _on_trigger_register(ctx: Any, trigger: Any) -> None:
  from .triggers import register_trigger

  register_trigger(trigger)


async def _on_trigger_remove(ctx: Any, trigger_id: str) -> None:
  from .triggers import remove_trigger

  remove_trigger(trigger_id)


# ---------------------------------------------------------------------------
# Tool-category toggle options
# ---------------------------------------------------------------------------

TOOL_CATEGORY_OPTIONS = [
  SkillOptionDefinition(
    name="enable_chat_tools",
    type="boolean",
    label="Enable Chat & Group Management",
    description="14 tools — create/archive/mute chats, join/leave groups, manage invite links",
    default=True,
    group="tool_categories",
    tool_filter=[
      "archive-chat",
      "create-channel",
      "create-group",
      "export-chat-invite",
      "get-chat",
      "get-chats",
      "get-invite-link",
      "import-chat-invite",
      "join-chat-by-link",
      "leave-chat",
      "list-chats",
      "mute-chat",
      "subscribe-public-channel",
      "unarchive-chat",
    ],
  ),
  SkillOptionDefinition(
    name="enable_message_tools",
    type="boolean",
    label="Enable Messaging & Reactions",
    description="25 tools — send/edit/delete/forward messages, reactions, polls, drafts, pins",
    default=True,
    group="tool_categories",
    tool_filter=[
      "clear-draft",
      "create-poll",
      "delete-message",
      "edit-message",
      "forward-message",
      "get-drafts",
      "get-history",
      "get-message-context",
      "get-message-reactions",
      "get-messages",
      "get-pinned-messages",
      "list-inline-buttons",
      "list-messages",
      "list-topics",
      "mark-as-read",
      "pin-message",
      "press-inline-button",
      "remove-reaction",
      "reply-to-message",
      "save-draft",
      "send-message",
      "send-reaction",
      "unmute-chat",
      "unpin-message",
      "get-recent-actions",
    ],
  ),
  SkillOptionDefinition(
    name="enable_contact_tools",
    type="boolean",
    label="Enable Contacts & Blocking",
    description="13 tools — add/delete/search/export contacts, block/unblock users",
    default=True,
    group="tool_categories",
    tool_filter=[
      "add-contact",
      "block-user",
      "delete-contact",
      "export-contacts",
      "get-blocked-users",
      "get-contact-chats",
      "get-contact-ids",
      "get-direct-chat-by-contact",
      "get-last-interaction",
      "import-contacts",
      "list-contacts",
      "search-contacts",
      "unblock-user",
    ],
  ),
  SkillOptionDefinition(
    name="enable_admin_tools",
    type="boolean",
    label="Enable Admin & Moderation",
    description="8 tools — promote/demote admins, ban/unban users, invite to groups",
    default=False,
    group="tool_categories",
    tool_filter=[
      "ban-user",
      "demote-admin",
      "get-admins",
      "get-banned-users",
      "get-participants",
      "invite-to-group",
      "promote-admin",
      "unban-user",
    ],
  ),
  SkillOptionDefinition(
    name="enable_profile_media_tools",
    type="boolean",
    label="Enable Profile & Media",
    description="10 tools — profile photos, chat photos, user status, bot info, media info",
    default=False,
    group="tool_categories",
    tool_filter=[
      "delete-chat-photo",
      "delete-profile-photo",
      "edit-chat-photo",
      "edit-chat-title",
      "get-bot-info",
      "get-me",
      "get-media-info",
      "get-user-photos",
      "get-user-status",
      "set-profile-photo",
    ],
  ),
  SkillOptionDefinition(
    name="enable_settings_tools",
    type="boolean",
    label="Enable Settings & Privacy",
    description="5 tools — privacy settings, profile updates, bot commands",
    default=False,
    group="tool_categories",
    tool_filter=[
      "get-privacy-settings",
      "resolve-username",
      "set-bot-commands",
      "set-privacy-settings",
      "update-profile",
    ],
  ),
  SkillOptionDefinition(
    name="enable_search_tools",
    type="boolean",
    label="Enable Search & Discovery",
    description="2 tools — search messages and public chats",
    default=True,
    group="tool_categories",
    tool_filter=[
      "search-messages",
      "search-public-chats",
    ],
  ),
]


# ---------------------------------------------------------------------------
# Skill definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
  name="telegram",
  description="Telegram integration via Telethon MTProto — 75+ tools for chats, messages, contacts, admin, media, and settings.",
  version="2.0.0",
  has_setup=True,
  has_disconnect=True,
  tick_interval=1_200_000,  # 20 minutes
  tools=_convert_tools(),
  options=TOOL_CATEGORY_OPTIONS,
  trigger_schema=TELEGRAM_TRIGGER_SCHEMA,
  hooks=SkillHooks(
    on_load=_on_load,
    on_unload=_on_unload,
    on_tick=_on_tick,
    on_status=_on_status,
    on_setup_start=on_setup_start,
    on_setup_submit=on_setup_submit,
    on_setup_cancel=on_setup_cancel,
    on_disconnect=_on_disconnect,
    on_trigger_register=_on_trigger_register,
    on_trigger_remove=_on_trigger_remove,
  ),
)
