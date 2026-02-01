"""
MCP server + skill lifecycle hooks.

Uses the official `mcp` Python SDK. Handles tools/list, tools/call,
and skill lifecycle methods (load, unload, tick, session events).
Integrates with the SkillServer from dev.runtime.server for reverse RPC.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .tools import ALL_TOOLS
from .handlers import dispatch_tool
from .client.telethon_client import create_client, get_client
from .state import store
from .state.sync import init_host_sync
from .db.connection import init_db, close_db, get_db
from .db.summaries import generate_summaries
from .entities import apply_summarization_results, emit_initial_entities, emit_summaries
from .events.handlers import register_event_handlers
from .sync.initial_sync import run_initial_sync

log = logging.getLogger("skill.telegram.server")


def create_mcp_server() -> Server:
  """Create and configure the MCP server with all tool handlers."""
  server = Server("telegram-skill")

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
  upsert_entity_fn: Any = None,
  upsert_relationship_fn: Any = None,
  request_summarization_fn: Any = None,
) -> None:
  """Called when the host loads this skill. Initializes Telethon + SQLite."""
  raw_api_id = os.environ.get("TELEGRAM_API_ID", params.get("apiId", "0")) or "0"
  api_id = int(raw_api_id) if str(raw_api_id).strip().isdigit() else 0
  api_hash = os.environ.get("TELEGRAM_API_HASH", params.get("apiHash", ""))
  session_string = params.get("sessionString", "")
  data_dir = params.get("dataDir", "data")

  log.info(
    "on_skill_load: api_id=%s, api_hash=%s..., session=%s, data_dir=%s, "
    "env_api_id=%s, env_api_hash=%s...",
    api_id,
    api_hash[:8] if api_hash else "<empty>",
    f"{session_string[:20]}..." if session_string else "<empty>",
    data_dir,
    os.environ.get("TELEGRAM_API_ID", "<not set>"),
    (os.environ.get("TELEGRAM_API_HASH", "") or "<not set>")[:8],
  )

  # Store entity callbacks and summarization callback for use in event handlers and tick
  _store_entity_callbacks(upsert_entity_fn, upsert_relationship_fn)
  _store_summarization_callback(request_summarization_fn)

  if not api_id or not api_hash:
    log.error("Missing TELEGRAM_API_ID or TELEGRAM_API_HASH")
    return

  # Initialize SQLite
  await init_db(data_dir)

  # Initialize Telethon client
  client = create_client(api_id, api_hash)
  await client.initialize(session_string)

  # Connect and check auth
  store.set_connection_status("connecting")
  try:
    await client.connect()
    store.set_connection_status("connected")

    is_authed = await client.check_connection()
    if is_authed:
      store.set_auth_status("authenticated")
      store.set_is_initialized(True)
      log.info("Telegram session is valid — authenticated")

      # Fetch current user
      me = await client.get_client().get_me()
      if me:
        from .client.builders import build_user

        store.set_current_user(build_user(me))

      # Register event handlers for real-time updates
      await register_event_handlers(client.get_client())

      # Launch initial sync as background task
      # (loads dialogs, caches users, preloads messages, emits entities)
      asyncio.create_task(
        _run_initial_sync_safe(
          client.get_client(),
          upsert_entity_fn,
          upsert_relationship_fn,
        )
      )
    else:
      store.set_auth_status("not_authenticated")
      log.warning(
        "Telegram session invalid or expired — disconnecting stale client. "
        "User will need to re-authenticate via setup."
      )
      # Disconnect to stop Telethon's background update loop from
      # spamming AuthKeyUnregisteredError on the stale session.
      try:
        await client.disconnect()
      except Exception:
        pass
  except Exception:
    log.exception("Failed to connect/authenticate")
    store.set_connection_status("error")

  # Initialize host sync if available
  if set_state_fn:
    init_host_sync(set_state_fn)

  log.info("Skill loaded successfully")


async def on_skill_unload() -> None:
  """Called when the host unloads this skill."""
  try:
    client = get_client()
    await client.disconnect()
  except Exception:
    log.exception("Error disconnecting client")

  await close_db()
  store.reset_state()
  log.info("Skill unloaded")


# ---------------------------------------------------------------------------
# Entity callback storage
# ---------------------------------------------------------------------------

_upsert_entity_fn: Any = None
_upsert_relationship_fn: Any = None
_request_summarization_fn: Any = None


def _store_entity_callbacks(
  upsert_entity: Any = None,
  upsert_relationship: Any = None,
) -> None:
  global _upsert_entity_fn, _upsert_relationship_fn
  _upsert_entity_fn = upsert_entity
  _upsert_relationship_fn = upsert_relationship


def _store_summarization_callback(request_summarization: Any = None) -> None:
  global _request_summarization_fn
  _request_summarization_fn = request_summarization


def get_entity_callbacks() -> tuple[Any, Any]:
  """Return the stored entity callbacks (for use by event handlers)."""
  return _upsert_entity_fn, _upsert_relationship_fn


async def _run_initial_sync_safe(
  client: Any,
  upsert_entity_fn: Any = None,
  upsert_relationship_fn: Any = None,
) -> None:
  """Wrapper to run initial sync without crashing the skill on failure."""
  try:
    await run_initial_sync(client, upsert_entity_fn, upsert_relationship_fn)
  except Exception:
    log.exception("Initial sync background task failed")


async def on_skill_tick() -> None:
  """Called periodically (every 20 minutes). Generates summaries + emits entities."""
  try:
    db = await get_db()
    await generate_summaries(db, store)
  except Exception:
    log.exception("Error during tick")

  # AI summarization via host reverse RPC
  if _request_summarization_fn and _upsert_entity_fn and _upsert_relationship_fn:
    try:
      db = await get_db()
      await _run_ai_summarization(db)
    except Exception:
      log.warning("AI summarization failed (host may not implement intelligence/summarize)")
      log.debug("AI summarization error details:", exc_info=True)

  # Emit summary entities and refresh chat/contact entities
  if _upsert_entity_fn and _upsert_relationship_fn:
    try:
      await emit_summaries(_upsert_entity_fn, _upsert_relationship_fn)
    except Exception:
      log.exception("Error emitting summary entities")

    try:
      await emit_initial_entities(_upsert_entity_fn, _upsert_relationship_fn)
    except Exception:
      log.exception("Error refreshing entities on tick")


# ---------------------------------------------------------------------------
# AI Summarization pipeline
# ---------------------------------------------------------------------------


async def _run_ai_summarization(db: Any) -> None:
  """Collect recent messages and send to host for AI summarization."""
  from .db.queries import get_recent_messages_for_summarization

  messages = await get_recent_messages_for_summarization(db)
  if not messages:
    log.debug("No recent messages for AI summarization")
    return

  chats = _build_chat_context()
  current_user = _build_current_user_context()

  log.info("Sending %d messages to host for AI summarization", len(messages))
  response = await _request_summarization_fn(
    messages=messages, chats=chats, current_user=current_user
  )

  if response and (_upsert_entity_fn and _upsert_relationship_fn):
    await apply_summarization_results(response, _upsert_entity_fn, _upsert_relationship_fn)


def _build_chat_context() -> list[dict[str, Any]]:
  """Build chat metadata list from current state for summarization context."""
  state = store.get_state()
  chats: list[dict[str, Any]] = []
  for chat_id in state.chats_order:
    chat = state.chats.get(chat_id)
    if not chat:
      continue
    chats.append(
      {
        "id": chat.id,
        "title": chat.title,
        "type": chat.type,
        "participants_count": chat.participants_count,
        "unread_count": chat.unread_count,
      }
    )
  return chats


def _build_current_user_context() -> dict[str, Any] | None:
  """Build current user metadata for summarization context."""
  state = store.get_state()
  user = state.current_user
  if not user:
    return None
  return {
    "id": user.id,
    "first_name": user.first_name,
    "username": user.username,
  }


async def run_server() -> None:
  """Run the MCP server on stdio."""
  server = create_mcp_server()
  async with stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, server.create_initialization_options())
