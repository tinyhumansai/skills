"""
Otter.ai SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.

Usage:
    from skills.otter.skill import skill
"""

from __future__ import annotations

import contextlib
import json
import logging
import time
from typing import Any

from dev.types.skill_types import (
  EntityPropertySchema,
  EntitySchema,
  EntityTypeDeclaration,
  RelationshipTypeDeclaration,
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

log = logging.getLogger("skill.otter.skill")


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
# Entity schema
# ---------------------------------------------------------------------------

ENTITY_SCHEMA = EntitySchema(
  entity_types=[
    EntityTypeDeclaration(
      type="otter.meeting",
      label="Otter Meeting",
      description="An Otter.ai meeting transcript/recording.",
      properties=[
        EntityPropertySchema(name="title", type="string", description="Meeting title"),
        EntityPropertySchema(name="duration", type="number", description="Duration in seconds"),
        EntityPropertySchema(
          name="created_at", type="number", description="Creation time as Unix timestamp"
        ),
        EntityPropertySchema(
          name="speaker_count", type="number", description="Number of speakers detected"
        ),
        EntityPropertySchema(
          name="word_count", type="number", description="Total word count of transcript"
        ),
        EntityPropertySchema(
          name="is_processed",
          type="boolean",
          description="Whether transcription is complete",
        ),
        EntityPropertySchema(
          name="summary", type="string", description="AI-generated summary", optional=True
        ),
      ],
    ),
    EntityTypeDeclaration(
      type="otter.speaker",
      label="Otter Speaker",
      description="A recognized speaker in Otter.ai meetings.",
      properties=[
        EntityPropertySchema(name="name", type="string", description="Speaker display name"),
      ],
    ),
    EntityTypeDeclaration(
      type="otter.summary",
      label="Otter Summary",
      description="A periodic digest summarizing recent meeting activity.",
      properties=[
        EntityPropertySchema(name="summary_type", type="string", description="Type of summary"),
        EntityPropertySchema(
          name="start_date", type="number", description="Period start as Unix timestamp"
        ),
        EntityPropertySchema(
          name="end_date", type="number", description="Period end as Unix timestamp"
        ),
      ],
    ),
  ],
  relationship_types=[
    RelationshipTypeDeclaration(
      type="speaker_in",
      source_type="otter.speaker",
      target_type="otter.meeting",
      description="Speaker participated in this meeting.",
      cardinality="many_to_many",
    ),
    RelationshipTypeDeclaration(
      type="summarizes",
      source_type="otter.summary",
      target_type="otter.meeting",
      description="Summary covers activity from this meeting.",
      cardinality="many_to_many",
    ),
  ],
)


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------


async def _on_load(ctx: Any) -> None:
  """Initialize Otter client + SQLite using SkillContext."""
  from .api import speech_api
  from .client.otter_client import OtterClient
  from .db.connection import init_db
  from .state import store
  from .state.sync import init_host_sync

  # Read config
  config: dict[str, Any] = {}
  try:
    raw = await ctx.read_data("config.json")
    if raw:
      config = json.loads(raw)
  except Exception:
    pass

  api_key = config.get("api_key", "")
  if not api_key:
    log.warning("No API key configured — Otter skill not initialized")
    store.set_connection_status("disconnected")
    return

  # Initialize state sync
  def set_state_fn(partial: dict[str, Any]) -> None:
    ctx.set_state(partial)

  init_host_sync(set_state_fn)

  # Initialize DB
  try:
    await init_db(ctx.data_dir)
  except Exception:
    log.exception("Failed to initialize database")

  # Initialize client
  client = OtterClient(api_key)
  try:
    store.set_connection_status("connecting")
    await client.connect()

    is_valid = await client.validate_key()
    if not is_valid:
      store.set_connection_error("Invalid API key")
      await client.close()
      return

    speech_api.set_client(client)
    store.set_connection_status("connected")
  except Exception as exc:
    log.exception("Failed to connect to Otter.ai")
    store.set_connection_error(str(exc))
    await client.close()
    return

  # Fetch initial data
  try:
    await speech_api.fetch_user()
  except Exception:
    log.debug("Failed to fetch user profile", exc_info=True)

  try:
    await speech_api.fetch_speeches(limit=50)
  except Exception:
    log.debug("Failed to fetch initial speeches", exc_info=True)

  try:
    await speech_api.fetch_speakers()
  except Exception:
    log.debug("Failed to fetch speakers", exc_info=True)

  store.set_is_initialized(True)
  store.set_sync_status(last_sync=time.time())

  # Emit entities (if the runtime exposes entity upsert methods)
  try:
    from .entities import emit_initial_entities

    upsert_fn = getattr(ctx.entities, "upsert", None) or (getattr(ctx, "_server", {}) and None)
    rel_fn = getattr(ctx.entities, "upsert_relationship", None)
    if upsert_fn and rel_fn:
      await emit_initial_entities(upsert_fn, rel_fn)
    else:
      log.debug("Entity upsert not available on context — skipping entity emission")
  except Exception:
    log.debug("Failed to emit initial entities", exc_info=True)

  log.info("Otter.ai skill loaded successfully")


async def _on_unload(ctx: Any) -> None:
  """Clean up resources."""
  from .api import speech_api
  from .db.connection import close_db
  from .state import store

  try:
    client = speech_api.get_client()
    await client.close()
  except Exception:
    pass

  with contextlib.suppress(Exception):
    await close_db()

  store.reset_state()
  log.info("Otter.ai skill unloaded")


async def _on_tick(ctx: Any) -> None:
  """Periodic sync — fetch new meetings, update cache, emit entities."""
  from .api import speech_api
  from .db import queries
  from .db.connection import get_db
  from .state import store

  state = store.get_state()
  if state.connection_status != "connected":
    return

  store.set_sync_status(is_syncing=True)

  # Fetch latest speeches
  try:
    old_ids = set(state.speeches_order)
    speeches = await speech_api.fetch_speeches(limit=50)
    new_ids = {s.speech_id for s in speeches} - old_ids

    # For new meetings, fetch transcripts and write to memory
    for speech_id in new_ids:
      try:
        segments = await speech_api.fetch_transcript(speech_id)
        if segments:
          speech = store.get_speech(speech_id)
          title = speech.title if speech else "Untitled"
          transcript_text = "\n".join(s.text for s in segments[:50])
          await ctx.memory.write(
            f"otter/meeting/{speech_id}",
            json.dumps(
              {
                "title": title,
                "speech_id": speech_id,
                "transcript_preview": transcript_text[:2000],
              }
            ),
          )
      except Exception:
        log.debug("Failed to fetch transcript for new meeting %s", speech_id, exc_info=True)

  except Exception:
    log.debug("Failed to fetch speeches on tick", exc_info=True)

  # Prune old data
  try:
    db = await get_db()
    await queries.prune_old_data(db)
  except Exception:
    log.debug("Failed to prune old data", exc_info=True)

  store.set_sync_status(is_syncing=False, last_sync=time.time())

  # Emit updated entities (if the runtime exposes entity upsert methods)
  try:
    from .entities import emit_initial_entities

    upsert_fn = getattr(ctx.entities, "upsert", None)
    rel_fn = getattr(ctx.entities, "upsert_relationship", None)
    if upsert_fn and rel_fn:
      await emit_initial_entities(upsert_fn, rel_fn)
  except Exception:
    log.debug("Failed to emit entities on tick", exc_info=True)


async def _on_status(ctx: Any) -> dict[str, Any]:
  """Return current skill status information."""
  from .state.store import get_state

  state = get_state()
  return {
    "connection_status": state.connection_status,
    "is_initialized": state.is_initialized,
    "connection_error": state.connection_error,
    "is_syncing": state.is_syncing,
    "last_sync": state.last_sync,
    "current_user": state.current_user.model_dump() if state.current_user else None,
    "total_meetings": state.total_meetings,
  }


# ---------------------------------------------------------------------------
# Disconnect handler
# ---------------------------------------------------------------------------


async def _on_disconnect(ctx: Any) -> None:
  """Close Otter client, close DB, and clear credentials."""
  from .api import speech_api
  from .db.connection import close_db
  from .state import store

  try:
    client = speech_api.get_client()
    await client.close()
  except Exception:
    pass

  with contextlib.suppress(Exception):
    await close_db()

  store.reset_state()

  try:
    await ctx.write_data("config.json", "{}")
  except Exception:
    log.warning("Failed to clear config.json on disconnect")


# ---------------------------------------------------------------------------
# Tool-category toggle options
# ---------------------------------------------------------------------------

TOOL_CATEGORY_OPTIONS = [
  SkillOptionDefinition(
    name="enable_meeting_tools",
    type="boolean",
    label="Meetings & Transcripts",
    description="8 tools — list, get, search, and download meetings, transcripts, speakers, and user profile",
    default=True,
    group="tool_categories",
    tool_filter=[
      "list_meetings",
      "get_meeting",
      "get_meeting_summary",
      "search_meetings",
      "search_in_meeting",
      "download_meeting_transcript",
      "get_otter_user",
      "list_speakers",
    ],
  ),
]


# ---------------------------------------------------------------------------
# Skill definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
  name="otter",
  description="Otter.ai meeting notes integration — fetch transcripts, summaries, and search across meetings.",
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
  entity_schema=ENTITY_SCHEMA,
)
