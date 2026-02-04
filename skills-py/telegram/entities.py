"""
Entity emission — converts Telegram state into platform entities and relationships.

Two main functions:
  - emit_initial_entities: Emits chats, contacts, and dm_with relationships on load.
  - emit_summaries: Emits summary entities and summarizes/summarizes_dm relationships on tick.

Both accept upsert_entity_fn and upsert_relationship_fn callables that forward
to the host runtime via reverse RPC.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from .db.connection import get_db
from .state import store

if TYPE_CHECKING:
  from .state.types import TelegramChat, TelegramUser

log = logging.getLogger("skill.telegram.entities")

SOURCE = "telegram"

# Type aliases for the callback signatures
UpsertEntityFn = Callable[..., Awaitable[None]]
UpsertRelationshipFn = Callable[..., Awaitable[None]]


def _chat_entity_type(chat: TelegramChat) -> str:
  """Map a TelegramChat to a platform entity type."""
  if chat.type == "channel":
    return "telegram.channel"
  if chat.type in ("group", "supergroup"):
    return "telegram.group"
  return "telegram.dm"


def _chat_metadata(chat: TelegramChat) -> dict[str, Any]:
  """Build metadata dict for a chat entity."""
  meta: dict[str, Any] = {
    "unread_count": chat.unread_count,
    "is_pinned": chat.is_pinned,
  }
  if chat.username:
    meta["username"] = chat.username
  if chat.participants_count is not None:
    meta["participants_count"] = chat.participants_count
  return meta


def _user_metadata(user: TelegramUser, is_self: bool = False) -> dict[str, Any]:
  """Build metadata dict for a contact entity."""
  meta: dict[str, Any] = {
    "first_name": user.first_name,
    "is_bot": user.is_bot,
  }
  if user.last_name:
    meta["last_name"] = user.last_name
  if user.username:
    meta["username"] = user.username
  if user.phone_number:
    meta["phone_number"] = user.phone_number
  if user.is_premium:
    meta["is_premium"] = True
  if is_self:
    meta["is_self"] = True
  return meta


async def emit_initial_entities(
  upsert_entity_fn: UpsertEntityFn,
  upsert_relationship_fn: UpsertRelationshipFn,
) -> None:
  """Emit all known chats and contacts as platform entities.

  Called after successful auth during on_skill_load, and again on each tick
  to refresh entity metadata (e.g. updated unread counts).
  """
  state = store.get_state()

  # --- Emit chat entities ---
  for chat_id in state.chats_order:
    chat = state.chats.get(chat_id)
    if not chat:
      continue

    entity_type = _chat_entity_type(chat)
    try:
      await upsert_entity_fn(
        type=entity_type,
        source=SOURCE,
        source_id=chat.id,
        title=chat.title or f"Chat {chat.id}",
        metadata=_chat_metadata(chat),
      )
    except Exception:
      log.debug("Failed to upsert chat entity %s", chat.id, exc_info=True)

    # Emit dm_with relationship for private chats
    if entity_type == "telegram.dm":
      try:
        await upsert_relationship_fn(
          source_id=f"{SOURCE}:{chat.id}",
          target_id=f"{SOURCE}:{chat.id}",
          type="dm_with",
          source=SOURCE,
        )
      except Exception:
        log.debug("Failed to upsert dm_with for %s", chat.id, exc_info=True)

  # --- Emit user/contact entities ---
  current_user = state.current_user
  current_user_id = current_user.id if current_user else None

  # Emit current user first
  if current_user:
    try:
      await upsert_entity_fn(
        type="telegram.contact",
        source=SOURCE,
        source_id=current_user.id,
        title=current_user.first_name or f"User {current_user.id}",
        metadata=_user_metadata(current_user, is_self=True),
      )
    except Exception:
      log.debug("Failed to upsert current user entity", exc_info=True)

  # Emit all known users
  for user_id, user in state.users.items():
    if user_id == current_user_id:
      continue  # Already emitted above
    try:
      await upsert_entity_fn(
        type="telegram.contact",
        source=SOURCE,
        source_id=user.id,
        title=user.first_name or f"User {user.id}",
        metadata=_user_metadata(user),
      )
    except Exception:
      log.debug("Failed to upsert user entity %s", user.id, exc_info=True)

  log.info(
    "Emitted entities: %d chats, %d contacts",
    len(state.chats_order),
    len(state.users) + (1 if current_user else 0),
  )


async def emit_summaries(
  upsert_entity_fn: UpsertEntityFn,
  upsert_relationship_fn: UpsertRelationshipFn,
) -> None:
  """Emit the latest summaries as platform entities with relationships.

  Called on each tick after summary generation. Reads the most recent
  summaries from SQLite and emits each as a telegram.summary entity,
  plus summarizes/summarizes_dm edges to referenced chats.
  """
  try:
    db = await get_db()
  except Exception:
    log.debug("Cannot get DB for summary emission", exc_info=True)
    return

  state = store.get_state()

  # Fetch the 4 most recent summaries (one per type)
  try:
    cursor = await db.execute(
      """SELECT summary_type, content, period_start, period_end
               FROM summaries
               ORDER BY created_at DESC
               LIMIT 4"""
    )
    rows = await cursor.fetchall()
  except Exception:
    log.debug("Failed to query summaries", exc_info=True)
    return

  import json

  for row in rows:
    summary_type = row[0]
    try:
      content = json.loads(row[1]) if isinstance(row[1], str) else row[1]
    except (json.JSONDecodeError, TypeError):
      content = {}
    period_start = row[2]
    period_end = row[3]

    entity_source_id = f"{summary_type}:{period_start}:{period_end}"

    # Build a human-readable title
    try:
      start_str = time.strftime("%b %d %H:%M", time.localtime(period_start))
      end_str = time.strftime("%H:%M", time.localtime(period_end))
    except (OSError, ValueError):
      start_str = str(period_start)
      end_str = str(period_end)

    title = f"{summary_type.replace('_', ' ').title()} Summary ({start_str} - {end_str})"

    # Summary-level metadata
    meta: dict[str, Any] = {
      "summary_type": summary_type,
      "start_date": period_start,
      "end_date": period_end,
      "content": content,
    }

    # Add type-specific top-level fields
    if summary_type == "activity":
      meta["total_messages"] = content.get("total_messages", 0)
      meta["active_chat_count"] = content.get("active_chat_count", 0)
    elif summary_type == "unread":
      meta["total_unread"] = content.get("total_unread", 0)
    elif summary_type == "mentions":
      meta["mention_count"] = content.get("mention_count", 0)

    try:
      await upsert_entity_fn(
        type="telegram.summary",
        source=SOURCE,
        source_id=entity_source_id,
        title=title,
        metadata=meta,
      )
    except Exception:
      log.debug("Failed to upsert summary entity %s", entity_source_id, exc_info=True)
      continue

    # Emit relationships to referenced chats
    referenced_chats = _extract_chat_ids_from_summary(content, summary_type)
    for chat_id in referenced_chats:
      chat = state.chats.get(chat_id)
      if not chat:
        continue

      entity_type = _chat_entity_type(chat)
      rel_type = "summarizes_dm" if entity_type == "telegram.dm" else "summarizes"

      try:
        await upsert_relationship_fn(
          source_id=f"{SOURCE}:{entity_source_id}",
          target_id=f"{SOURCE}:{chat_id}",
          type=rel_type,
          source=SOURCE,
        )
      except Exception:
        log.debug(
          "Failed to upsert %s relationship for %s -> %s",
          rel_type,
          entity_source_id,
          chat_id,
          exc_info=True,
        )

  log.info("Emitted %d summary entities", len(list(rows)))


async def apply_summarization_results(
  response: dict[str, Any],
  upsert_entity_fn: UpsertEntityFn,
  upsert_relationship_fn: UpsertRelationshipFn,
) -> None:
  """Process AI summarization response — create topic entities + relationships."""

  # Create topic entities
  for topic in response.get("topics", []):
    try:
      await upsert_entity_fn(
        type="telegram.topic",
        source=SOURCE,
        source_id=topic["id"],
        title=topic["name"],
        summary=topic.get("description"),
        metadata=topic.get("metadata", {}),
      )
    except Exception:
      log.debug("Failed to upsert topic entity %s", topic.get("id"), exc_info=True)

  # Create relationships
  for conn in response.get("connections", []):
    try:
      await upsert_relationship_fn(
        source_id=conn["sourceId"],
        target_id=conn["targetId"],
        type=conn["type"],
        source=SOURCE,
        metadata=conn.get("metadata", {}),
      )
    except Exception:
      log.debug(
        "Failed to upsert relationship %s -> %s",
        conn.get("sourceId"),
        conn.get("targetId"),
        exc_info=True,
      )

  # Store AI summaries as enhanced summary entities
  for summary in response.get("summaries", []):
    try:
      await upsert_entity_fn(
        type="telegram.ai_summary",
        source=SOURCE,
        source_id=f"ai_summary:{summary['chatId']}:{int(time.time())}",
        title=f"AI Summary — {summary.get('chatTitle', summary['chatId'])}",
        summary=summary["summary"],
        metadata={"chat_id": summary["chatId"]},
      )
    except Exception:
      log.debug("Failed to upsert AI summary for chat %s", summary.get("chatId"), exc_info=True)

  topic_count = len(response.get("topics", []))
  conn_count = len(response.get("connections", []))
  summary_count = len(response.get("summaries", []))
  log.info(
    "Applied AI summarization: %d topics, %d connections, %d summaries",
    topic_count,
    conn_count,
    summary_count,
  )


def _extract_chat_ids_from_summary(content: dict[str, Any], summary_type: str) -> list[str]:
  """Extract chat IDs referenced in a summary's content."""
  chat_ids: list[str] = []

  if summary_type == "activity":
    for chat_info in content.get("active_chats", []):
      cid = chat_info.get("chat_id")
      if cid:
        chat_ids.append(str(cid))

  elif summary_type == "unread":
    for chat_info in content.get("unread_chats", []):
      cid = chat_info.get("chat_id")
      if cid:
        chat_ids.append(str(cid))

  elif summary_type == "top_chats":
    for chat_info in content.get("top_chats", []):
      cid = chat_info.get("chat_id")
      if cid:
        chat_ids.append(str(cid))

  elif summary_type == "mentions":
    seen: set[str] = set()
    for mention in content.get("mentions", []):
      cid = mention.get("chat_id")
      if cid and str(cid) not in seen:
        chat_ids.append(str(cid))
        seen.add(str(cid))

  return chat_ids
