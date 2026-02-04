"""
Read/write query functions for the SQLite database.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
  import aiosqlite

  from ..state.types import TelegramChat, TelegramMessage, TelegramUser

log = logging.getLogger("skill.telegram.db.queries")


# ---------------------------------------------------------------------------
# Skill state (key-value)
# ---------------------------------------------------------------------------


async def get_skill_state(db: aiosqlite.Connection, key: str) -> str | None:
  cursor = await db.execute("SELECT value FROM skill_state WHERE key = ?", (key,))
  row = await cursor.fetchone()
  return row[0] if row else None


async def set_skill_state(db: aiosqlite.Connection, key: str, value: str) -> None:
  await db.execute(
    "INSERT OR REPLACE INTO skill_state (key, value, updated_at) VALUES (?, ?, ?)",
    (key, value, time.time()),
  )
  await db.commit()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


async def upsert_user(db: aiosqlite.Connection, user: TelegramUser) -> None:
  await db.execute(
    """INSERT OR REPLACE INTO users
           (id, first_name, last_name, username, phone_number, is_bot, is_verified, is_premium, access_hash, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (
      user.id,
      user.first_name,
      user.last_name,
      user.username,
      user.phone_number,
      int(user.is_bot),
      int(user.is_verified) if user.is_verified is not None else None,
      int(user.is_premium) if user.is_premium is not None else None,
      user.access_hash,
      time.time(),
    ),
  )


async def upsert_users_batch(db: aiosqlite.Connection, users: list[TelegramUser]) -> None:
  for user in users:
    await upsert_user(db, user)
  await db.commit()


# ---------------------------------------------------------------------------
# Chats
# ---------------------------------------------------------------------------


async def upsert_chat(db: aiosqlite.Connection, chat: TelegramChat, sort_order: int = 0) -> None:
  await db.execute(
    """INSERT OR REPLACE INTO chats
           (id, title, type, username, access_hash, unread_count, is_pinned,
            participants_count, last_message_id, last_message_date, sort_order, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (
      chat.id,
      chat.title,
      chat.type,
      chat.username,
      chat.access_hash,
      chat.unread_count,
      int(chat.is_pinned),
      chat.participants_count,
      chat.last_message.id if chat.last_message else None,
      chat.last_message_date,
      sort_order,
      time.time(),
    ),
  )


async def upsert_chats_batch(db: aiosqlite.Connection, chats: list[TelegramChat]) -> None:
  for i, chat in enumerate(chats):
    await upsert_chat(db, chat, sort_order=i)
  await db.commit()


async def get_chats(db: aiosqlite.Connection, limit: int = 100) -> list[dict[str, Any]]:
  cursor = await db.execute("SELECT * FROM chats ORDER BY sort_order ASC LIMIT ?", (limit,))
  rows = await cursor.fetchall()
  return [dict(row) for row in rows]


async def delete_chat(db: aiosqlite.Connection, chat_id: str) -> None:
  await db.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
  await db.commit()


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


async def upsert_message(db: aiosqlite.Connection, msg: TelegramMessage) -> None:
  await db.execute(
    """INSERT OR REPLACE INTO messages
           (id, chat_id, date, message, from_id, from_name, is_outgoing,
            is_edited, is_forwarded, reply_to_message_id, thread_id, media_type, views, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (
      msg.id,
      msg.chat_id,
      msg.date,
      msg.message,
      msg.from_id,
      msg.from_name,
      int(msg.is_outgoing),
      int(msg.is_edited),
      int(msg.is_forwarded),
      msg.reply_to_message_id,
      msg.thread_id,
      msg.media.get("type") if msg.media else None,
      msg.views,
      time.time(),
    ),
  )


async def upsert_messages_batch(db: aiosqlite.Connection, messages: list[TelegramMessage]) -> None:
  for msg in messages:
    await upsert_message(db, msg)
  await db.commit()


async def delete_message(db: aiosqlite.Connection, chat_id: str, message_id: str) -> None:
  await db.execute("DELETE FROM messages WHERE chat_id = ? AND id = ?", (chat_id, message_id))
  await db.commit()


async def get_messages(
  db: aiosqlite.Connection, chat_id: str, limit: int = 50
) -> list[dict[str, Any]]:
  cursor = await db.execute(
    "SELECT * FROM messages WHERE chat_id = ? ORDER BY date DESC LIMIT ?",
    (chat_id, limit),
  )
  rows = await cursor.fetchall()
  return [dict(row) for row in rows]


async def get_messages_since(
  db: aiosqlite.Connection, since: float, limit: int = 500
) -> list[dict[str, Any]]:
  cursor = await db.execute(
    "SELECT * FROM messages WHERE date >= ? ORDER BY date DESC LIMIT ?",
    (since, limit),
  )
  rows = await cursor.fetchall()
  return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


async def insert_event(
  db: aiosqlite.Connection,
  event_type: str,
  chat_id: str | None,
  data: Any,
) -> None:
  await db.execute(
    "INSERT INTO events (event_type, chat_id, data, created_at) VALUES (?, ?, ?, ?)",
    (event_type, chat_id, json.dumps(data), time.time()),
  )
  await db.commit()


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


async def insert_summary(
  db: aiosqlite.Connection,
  summary_type: str,
  content: Any,
  period_start: float,
  period_end: float,
) -> None:
  await db.execute(
    "INSERT INTO summaries (summary_type, content, period_start, period_end, created_at) VALUES (?, ?, ?, ?, ?)",
    (summary_type, json.dumps(content), period_start, period_end, time.time()),
  )
  await db.commit()


async def prune_old_data(db: aiosqlite.Connection) -> None:
  """Remove old summaries (>24h) and events (>1h)."""
  now = time.time()
  await db.execute("DELETE FROM summaries WHERE created_at < ?", (now - 86400,))
  await db.execute("DELETE FROM events WHERE created_at < ?", (now - 3600,))
  await db.commit()


# ---------------------------------------------------------------------------
# Update state (for resumable sync)
# ---------------------------------------------------------------------------


async def get_update_state(db: aiosqlite.Connection) -> dict[str, int] | None:
  cursor = await db.execute("SELECT pts, qts, date, seq FROM update_state WHERE key = 'global'")
  row = await cursor.fetchone()
  if not row:
    return None
  return {"pts": row[0], "qts": row[1], "date": row[2], "seq": row[3]}


async def set_update_state(
  db: aiosqlite.Connection, pts: int, qts: int, date: int, seq: int
) -> None:
  await db.execute(
    """INSERT OR REPLACE INTO update_state (key, pts, qts, date, seq, updated_at)
           VALUES ('global', ?, ?, ?, ?, ?)""",
    (pts, qts, date, seq, time.time()),
  )
  await db.commit()


# ---------------------------------------------------------------------------
# Channel pts tracking
# ---------------------------------------------------------------------------


async def get_channel_pts(db: aiosqlite.Connection, channel_id: str) -> int | None:
  cursor = await db.execute("SELECT pts FROM channel_pts WHERE channel_id = ?", (channel_id,))
  row = await cursor.fetchone()
  return row[0] if row else None


async def set_channel_pts(db: aiosqlite.Connection, channel_id: str, pts: int) -> None:
  await db.execute(
    """INSERT OR REPLACE INTO channel_pts (channel_id, pts, updated_at)
           VALUES (?, ?, ?)""",
    (channel_id, pts, time.time()),
  )
  await db.commit()


async def get_all_channel_pts(db: aiosqlite.Connection) -> dict[str, int]:
  cursor = await db.execute("SELECT channel_id, pts FROM channel_pts")
  rows = await cursor.fetchall()
  return {row[0]: row[1] for row in rows}


# ---------------------------------------------------------------------------
# AI Summarization support
# ---------------------------------------------------------------------------


async def get_recent_messages_for_summarization(
  db: aiosqlite.Connection,
  since: float | None = None,
  limit: int = 1000,
) -> list[dict[str, Any]]:
  """Fetch recent messages with content for AI summarization.

  Returns a flat list with chat_id for grouping.
  Only includes messages with non-empty text content.
  """
  if since is None:
    since = time.time() - 1200  # last 20 minutes

  cursor = await db.execute(
    """SELECT m.id, m.chat_id, m.date, m.message, m.from_id, m.from_name,
              m.is_outgoing, m.reply_to_message_id, m.thread_id,
              c.title AS chat_title, c.type AS chat_type
       FROM messages m
       LEFT JOIN chats c ON m.chat_id = c.id
       WHERE m.date >= ? AND m.message IS NOT NULL AND m.message != ''
       ORDER BY m.chat_id, m.date ASC
       LIMIT ?""",
    (since, limit),
  )
  rows = await cursor.fetchall()
  columns = [desc[0] for desc in cursor.description]
  return [dict(zip(columns, row, strict=False)) for row in rows]
