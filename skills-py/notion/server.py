"""
Skill lifecycle hooks for the Notion skill.

Handles load, unload, and tick events. Unlike Telegram, Notion has no
real-time event stream or persistent connection — it's purely API-based.
"""

from __future__ import annotations

import logging
from typing import Any

from .client import close_client, create_client, get_client
from .entities import emit_initial_entities

log = logging.getLogger("skill.notion.server")


# ---------------------------------------------------------------------------
# Entity callback storage
# ---------------------------------------------------------------------------

_upsert_entity_fn: Any = None
_upsert_relationship_fn: Any = None


def _store_entity_callbacks(
  upsert_entity: Any = None,
  upsert_relationship: Any = None,
) -> None:
  global _upsert_entity_fn, _upsert_relationship_fn
  _upsert_entity_fn = upsert_entity
  _upsert_relationship_fn = upsert_relationship


def get_entity_callbacks() -> tuple[Any, Any]:
  """Return the stored entity callbacks."""
  return _upsert_entity_fn, _upsert_relationship_fn


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------


async def on_skill_load(
  params: dict[str, Any],
  set_state_fn: Any = None,
  upsert_entity_fn: Any = None,
  upsert_relationship_fn: Any = None,
) -> None:
  """Called when the host loads this skill. Initializes the Notion client."""
  token = params.get("token", "")

  # Store entity callbacks
  _store_entity_callbacks(upsert_entity_fn, upsert_relationship_fn)

  if not token:
    log.error("Missing Notion integration token")
    return

  # Create client
  client = create_client(token)

  # Validate token
  try:
    me = await client.users.me()
    bot_name = me.get("name", "integration")
    log.info("Connected to Notion as '%s'", bot_name)

    if set_state_fn:
      set_state_fn(
        {
          "connected": True,
          "bot_name": bot_name,
          "bot_id": me.get("id", ""),
        }
      )
  except Exception:
    log.exception("Failed to validate Notion token")
    if set_state_fn:
      set_state_fn({"connected": False, "error": "Token validation failed"})
    return

  # Emit initial entities
  if upsert_entity_fn and upsert_relationship_fn:
    try:
      await emit_initial_entities(upsert_entity_fn, upsert_relationship_fn)
    except Exception:
      log.exception("Failed to emit initial entities")

  log.info("Notion skill loaded successfully")


async def on_skill_unload() -> None:
  """Called when the host unloads this skill."""
  close_client()
  _store_entity_callbacks(None, None)
  log.info("Notion skill unloaded")


async def on_skill_tick() -> None:
  """Called periodically (every 5 minutes). Re-fetches and re-emits entities."""
  if not _upsert_entity_fn or not _upsert_relationship_fn:
    return

  # Verify client is still valid
  try:
    client = get_client()
    await client.users.me()
  except Exception:
    log.warning("Notion client not available or token expired during tick")
    return

  try:
    await emit_initial_entities(_upsert_entity_fn, _upsert_relationship_fn)
  except Exception:
    log.exception("Error refreshing entities on tick")
