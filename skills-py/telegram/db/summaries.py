"""
Periodic summary generation — called every 20 minutes by on_tick.

Generates four summary types:
  1. activity  — Recent chat activity (which chats had new messages, counts)
  2. unread    — Current unread counts by chat, total unread
  3. top_chats — Most active chats in the period ranked by message count
  4. mentions  — Messages mentioning the current user or containing keywords

Also prunes old summaries (>24h) and events (>1h).
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from ..db.queries import insert_summary, prune_old_data

if TYPE_CHECKING:
  import aiosqlite

log = logging.getLogger("skill.telegram.db.summaries")

PERIOD_SECONDS = 1200  # 20 minutes


async def generate_summaries(
  db: aiosqlite.Connection,
  store: Any,
) -> None:
  """Generate all summary types and persist to SQLite."""
  now = time.time()
  period_start = now - PERIOD_SECONDS

  try:
    # 1. Activity summary
    activity = await _build_activity_summary(db, period_start, now)
    await insert_summary(db, "activity", activity, period_start, now)

    # 2. Unread summary
    unread = _build_unread_summary(store)
    await insert_summary(db, "unread", unread, period_start, now)

    # 3. Top chats
    top = await _build_top_chats_summary(db, period_start, now)
    await insert_summary(db, "top_chats", top, period_start, now)

    # 4. Mentions
    mentions = await _build_mentions_summary(db, store, period_start, now)
    await insert_summary(db, "mentions", mentions, period_start, now)

    # Prune old data
    await prune_old_data(db)

    log.info(
      "Summaries generated for period %s - %s",
      period_start,
      now,
    )
  except Exception:
    log.exception("Error generating summaries")


async def _build_activity_summary(
  db: aiosqlite.Connection,
  period_start: float,
  period_end: float,
) -> dict[str, Any]:
  """Build activity summary: which chats had new messages, counts, active users."""
  # Count messages per chat in the period
  cursor = await db.execute(
    """SELECT chat_id, COUNT(*) as msg_count, COUNT(DISTINCT from_id) as unique_senders
           FROM messages
           WHERE date >= ? AND date <= ?
           GROUP BY chat_id
           ORDER BY msg_count DESC
           LIMIT 50""",
    (period_start, period_end),
  )
  rows = await cursor.fetchall()

  active_chats = []
  total_messages = 0
  total_unique_senders = set()

  for row in rows:
    chat_id = row[0]
    msg_count = row[1]
    unique_senders = row[2]
    total_messages += msg_count

    # Get chat title from chats table
    title_cursor = await db.execute("SELECT title, type FROM chats WHERE id = ?", (chat_id,))
    title_row = await title_cursor.fetchone()
    title = title_row[0] if title_row else f"Chat {chat_id}"
    chat_type = title_row[1] if title_row else "unknown"

    active_chats.append(
      {
        "chat_id": chat_id,
        "title": title,
        "type": chat_type,
        "message_count": msg_count,
        "unique_senders": unique_senders,
      }
    )

  # Get distinct senders
  sender_cursor = await db.execute(
    "SELECT DISTINCT from_id FROM messages WHERE date >= ? AND date <= ? AND from_id IS NOT NULL",
    (period_start, period_end),
  )
  sender_rows = await sender_cursor.fetchall()
  total_unique_senders = {row[0] for row in sender_rows}

  return {
    "total_messages": total_messages,
    "active_chat_count": len(active_chats),
    "unique_senders": len(total_unique_senders),
    "active_chats": active_chats[:20],
    "period_start": period_start,
    "period_end": period_end,
  }


def _build_unread_summary(store: Any) -> dict[str, Any]:
  """Build unread summary from in-memory store."""
  state = store.get_state()
  unread_chats = []
  total_unread = 0

  for chat_id in state.chats_order:
    chat = state.chats.get(chat_id)
    if chat and chat.unread_count > 0:
      total_unread += chat.unread_count
      unread_chats.append(
        {
          "chat_id": chat.id,
          "title": chat.title or f"Chat {chat.id}",
          "type": chat.type,
          "unread_count": chat.unread_count,
        }
      )

  # Sort by unread count descending
  unread_chats.sort(key=lambda x: x["unread_count"], reverse=True)

  return {
    "total_unread": total_unread,
    "unread_chat_count": len(unread_chats),
    "unread_chats": unread_chats[:30],
  }


async def _build_top_chats_summary(
  db: aiosqlite.Connection,
  period_start: float,
  period_end: float,
) -> dict[str, Any]:
  """Build top chats ranked by message count in the period."""
  cursor = await db.execute(
    """SELECT chat_id, COUNT(*) as msg_count
           FROM messages
           WHERE date >= ? AND date <= ?
           GROUP BY chat_id
           ORDER BY msg_count DESC
           LIMIT 10""",
    (period_start, period_end),
  )
  rows = await cursor.fetchall()

  top_chats = []
  for row in rows:
    chat_id = row[0]
    msg_count = row[1]

    title_cursor = await db.execute("SELECT title, type FROM chats WHERE id = ?", (chat_id,))
    title_row = await title_cursor.fetchone()
    title = title_row[0] if title_row else f"Chat {chat_id}"
    chat_type = title_row[1] if title_row else "unknown"

    top_chats.append(
      {
        "chat_id": chat_id,
        "title": title,
        "type": chat_type,
        "message_count": msg_count,
      }
    )

  return {
    "top_chats": top_chats,
    "period_start": period_start,
    "period_end": period_end,
  }


async def _build_mentions_summary(
  db: aiosqlite.Connection,
  store: Any,
  period_start: float,
  period_end: float,
) -> dict[str, Any]:
  """Build mentions summary — messages mentioning the current user."""
  state = store.get_state()
  current_user = state.current_user

  if not current_user:
    return {
      "mention_count": 0,
      "mentions": [],
      "period_start": period_start,
      "period_end": period_end,
    }

  # Build search terms: username, first name
  search_terms = []
  if current_user.username:
    search_terms.append(f"@{current_user.username}")
  if current_user.first_name:
    search_terms.append(current_user.first_name)

  if not search_terms:
    return {
      "mention_count": 0,
      "mentions": [],
      "period_start": period_start,
      "period_end": period_end,
    }

  # Build SQL LIKE conditions
  conditions = " OR ".join("message LIKE ?" for _ in search_terms)
  params: list[Any] = [period_start, period_end]
  for term in search_terms:
    params.append(f"%{term}%")

  cursor = await db.execute(
    f"""SELECT id, chat_id, date, message, from_id, from_name
            FROM messages
            WHERE date >= ? AND date <= ?
              AND is_outgoing = 0
              AND ({conditions})
            ORDER BY date DESC
            LIMIT 50""",
    params,
  )
  rows = await cursor.fetchall()

  mentions = []
  for row in rows:
    msg_id, chat_id, date, message, from_id, from_name = row
    # Get chat title
    title_cursor = await db.execute("SELECT title FROM chats WHERE id = ?", (chat_id,))
    title_row = await title_cursor.fetchone()
    chat_title = title_row[0] if title_row else f"Chat {chat_id}"

    mentions.append(
      {
        "message_id": msg_id,
        "chat_id": chat_id,
        "chat_title": chat_title,
        "date": date,
        "text": (message or "")[:200],
        "from_id": from_id,
        "from_name": from_name,
      }
    )

  return {
    "mention_count": len(mentions),
    "mentions": mentions,
    "period_start": period_start,
    "period_end": period_end,
  }
