"""
Entity emission — converts Notion pages, databases, and users into platform entities.

Two main functions:
  - emit_initial_entities: Emits pages, databases, and users on load.
  - emit_all_entities: Re-emits everything on tick (captures new/renamed/archived items).

Both accept upsert_entity_fn and upsert_relationship_fn callables that forward
to the host runtime via reverse RPC.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from .client import get_client
from .helpers import _rich_text_to_str, enforce_rate_limit, extract_title

log = logging.getLogger("skill.notion.entities")

SOURCE = "notion"

# Type aliases for the callback signatures
UpsertEntityFn = Callable[..., Awaitable[None]]
UpsertRelationshipFn = Callable[..., Awaitable[None]]


async def emit_initial_entities(
  upsert_entity_fn: UpsertEntityFn,
  upsert_relationship_fn: UpsertRelationshipFn,
) -> None:
  """Emit all accessible pages, databases, and users as platform entities.

  Called after successful auth during on_skill_load, and again on each tick
  to refresh entity metadata.
  """
  client = get_client()
  page_count = 0
  db_count = 0
  user_count = 0

  # --- Emit pages ---
  try:
    await enforce_rate_limit("read")
    response = await client.search(
      filter={"property": "object", "value": "page"},
      page_size=100,
    )
    pages = response.get("results", [])

    for page in pages:
      try:
        await _emit_page_entity(page, upsert_entity_fn, upsert_relationship_fn)
        page_count += 1
      except Exception:
        log.debug("Failed to emit page entity %s", page.get("id"), exc_info=True)
  except Exception:
    log.exception("Failed to search pages for entity emission")

  # --- Emit databases ---
  try:
    await enforce_rate_limit("read")
    response = await client.search(
      filter={"property": "object", "value": "database"},
      page_size=100,
    )
    databases = response.get("results", [])

    for db in databases:
      try:
        await _emit_database_entity(db, upsert_entity_fn)
        db_count += 1
      except Exception:
        log.debug("Failed to emit database entity %s", db.get("id"), exc_info=True)
  except Exception:
    log.exception("Failed to search databases for entity emission")

  # --- Emit users ---
  try:
    await enforce_rate_limit("read")
    response = await client.users.list(page_size=100)
    users = response.get("results", [])

    for user in users:
      try:
        await _emit_user_entity(user, upsert_entity_fn)
        user_count += 1
      except Exception:
        log.debug("Failed to emit user entity %s", user.get("id"), exc_info=True)
  except Exception:
    log.exception("Failed to list users for entity emission")

  log.info("Emitted entities: %d pages, %d databases, %d users", page_count, db_count, user_count)


async def _emit_page_entity(
  page: dict[str, Any],
  upsert_entity_fn: UpsertEntityFn,
  upsert_relationship_fn: UpsertRelationshipFn,
) -> None:
  """Emit a single page as a notion.page entity with relationships."""
  page_id = page.get("id", "")
  title = extract_title(page)
  url = page.get("url", "")

  # Build metadata
  meta: dict[str, Any] = {
    "url": url,
    "last_edited_time": page.get("last_edited_time", ""),
    "created_time": page.get("created_time", ""),
    "archived": page.get("archived", False),
  }

  # Icon
  icon = page.get("icon")
  if icon:
    if icon.get("type") == "emoji":
      meta["icon"] = icon.get("emoji", "")
    elif icon.get("type") == "external":
      meta["icon"] = icon.get("external", {}).get("url", "")

  # Parent type
  parent = page.get("parent", {})
  parent_type = parent.get("type", "")
  meta["parent_type"] = parent_type

  await upsert_entity_fn(
    type="notion.page",
    source=SOURCE,
    source_id=page_id,
    title=title or f"Page {page_id}",
    metadata=meta,
  )

  # --- Relationships ---

  # child_of: page → parent page
  if parent_type == "page_id":
    parent_page_id = parent.get("page_id", "")
    if parent_page_id:
      await upsert_relationship_fn(
        source_id=f"{SOURCE}:{page_id}",
        target_id=f"{SOURCE}:{parent_page_id}",
        type="child_of",
        source=SOURCE,
      )

  # entry_in: page → parent database
  if parent_type == "database_id":
    parent_db_id = parent.get("database_id", "")
    if parent_db_id:
      await upsert_relationship_fn(
        source_id=f"{SOURCE}:{page_id}",
        target_id=f"{SOURCE}:{parent_db_id}",
        type="entry_in",
        source=SOURCE,
      )

  # created_by: page → user
  created_by = page.get("created_by", {})
  if created_by.get("id"):
    await upsert_relationship_fn(
      source_id=f"{SOURCE}:{page_id}",
      target_id=f"{SOURCE}:{created_by['id']}",
      type="created_by",
      source=SOURCE,
    )

  # last_edited_by: page → user
  last_edited_by = page.get("last_edited_by", {})
  if last_edited_by.get("id"):
    await upsert_relationship_fn(
      source_id=f"{SOURCE}:{page_id}",
      target_id=f"{SOURCE}:{last_edited_by['id']}",
      type="last_edited_by",
      source=SOURCE,
    )


async def _emit_database_entity(
  db: dict[str, Any],
  upsert_entity_fn: UpsertEntityFn,
) -> None:
  """Emit a single database as a notion.database entity."""
  db_id = db.get("id", "")
  title = extract_title(db)
  url = db.get("url", "")
  desc_parts = db.get("description", [])
  description = _rich_text_to_str(desc_parts) if isinstance(desc_parts, list) else ""
  props = db.get("properties", {})

  meta: dict[str, Any] = {
    "url": url,
    "last_edited_time": db.get("last_edited_time", ""),
    "created_time": db.get("created_time", ""),
    "archived": db.get("archived", False),
    "property_count": len(props),
  }

  if description:
    meta["description"] = description

  icon = db.get("icon")
  if icon:
    if icon.get("type") == "emoji":
      meta["icon"] = icon.get("emoji", "")
    elif icon.get("type") == "external":
      meta["icon"] = icon.get("external", {}).get("url", "")

  await upsert_entity_fn(
    type="notion.database",
    source=SOURCE,
    source_id=db_id,
    title=title or f"Database {db_id}",
    metadata=meta,
  )


async def _emit_user_entity(
  user: dict[str, Any],
  upsert_entity_fn: UpsertEntityFn,
) -> None:
  """Emit a single user as a notion.user entity."""
  user_id = user.get("id", "")
  name = user.get("name", "Unknown")
  user_type = user.get("type", "unknown")

  meta: dict[str, Any] = {
    "user_type": user_type,
  }

  # Email (only for person type)
  if user.get("person"):
    email = user["person"].get("email", "")
    if email:
      meta["email"] = email

  # Avatar
  avatar_url = user.get("avatar_url", "")
  if avatar_url:
    meta["avatar_url"] = avatar_url

  await upsert_entity_fn(
    type="notion.user",
    source=SOURCE,
    source_id=user_id,
    title=name,
    metadata=meta,
  )
