"""
Typed query helpers for the email database.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from ..state.types import EmailAddress, EmailAttachment, EmailContact, ParsedEmail

if TYPE_CHECKING:
  import aiosqlite

log = logging.getLogger("skill.email.db.queries")


# ---------------------------------------------------------------------------
# Emails
# ---------------------------------------------------------------------------


async def upsert_email(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
  email: ParsedEmail,
) -> None:
  """Insert or update a cached email."""
  now = time.time()
  await db.execute(
    """
        INSERT INTO emails (
            account_id, folder, uid, message_id_header, in_reply_to,
            references_header, thread_id, from_addr, from_name,
            to_addrs, cc_addrs, subject, date,
            body_text, body_html, body_preview, fetched_body,
            is_read, is_flagged, is_answered, is_draft,
            has_attachments, attachment_count, attachments_json,
            raw_size, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (account_id, folder, uid) DO UPDATE SET
            message_id_header = excluded.message_id_header,
            in_reply_to = excluded.in_reply_to,
            references_header = excluded.references_header,
            thread_id = excluded.thread_id,
            from_addr = excluded.from_addr,
            from_name = excluded.from_name,
            to_addrs = excluded.to_addrs,
            cc_addrs = excluded.cc_addrs,
            subject = excluded.subject,
            date = excluded.date,
            body_text = CASE WHEN excluded.fetched_body = 1 THEN excluded.body_text ELSE emails.body_text END,
            body_html = CASE WHEN excluded.fetched_body = 1 THEN excluded.body_html ELSE emails.body_html END,
            body_preview = excluded.body_preview,
            fetched_body = CASE WHEN excluded.fetched_body = 1 THEN 1 ELSE emails.fetched_body END,
            is_read = excluded.is_read,
            is_flagged = excluded.is_flagged,
            is_answered = excluded.is_answered,
            is_draft = excluded.is_draft,
            has_attachments = excluded.has_attachments,
            attachment_count = excluded.attachment_count,
            attachments_json = excluded.attachments_json,
            raw_size = excluded.raw_size,
            updated_at = excluded.updated_at
        """,
    (
      account_id,
      folder,
      email.uid,
      email.message_id,
      email.in_reply_to,
      json.dumps(email.references),
      email.thread_id,
      email.from_addr.email if email.from_addr else None,
      email.from_addr.display_name if email.from_addr else None,
      json.dumps([a.model_dump() for a in email.to_addrs]),
      json.dumps([a.model_dump() for a in email.cc_addrs]),
      email.subject,
      email.date,
      email.body_text,
      email.body_html,
      email.body_preview,
      1 if email.body_text or email.body_html else 0,
      int(email.is_read),
      int(email.is_flagged),
      int(email.is_answered),
      int(email.is_draft),
      int(email.has_attachments),
      email.attachment_count,
      json.dumps([a.model_dump() for a in email.attachments]),
      email.raw_size,
      now,
    ),
  )
  await db.commit()


async def upsert_emails_batch(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
  emails: list[ParsedEmail],
) -> None:
  """Batch insert/update cached emails."""
  for email in emails:
    await upsert_email(db, account_id, folder, email)


async def get_cached_email(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
  uid: int,
) -> ParsedEmail | None:
  """Get a cached email by UID."""
  cursor = await db.execute(
    "SELECT * FROM emails WHERE account_id = ? AND folder = ? AND uid = ?",
    (account_id, folder, uid),
  )
  row = await cursor.fetchone()
  if not row:
    return None
  return _row_to_parsed_email(row)


async def get_cached_email_by_message_id(
  db: aiosqlite.Connection,
  account_id: str,
  message_id: str,
) -> tuple[str, ParsedEmail] | None:
  """Get a cached email by Message-ID header. Returns (folder, email)."""
  cursor = await db.execute(
    "SELECT * FROM emails WHERE account_id = ? AND message_id_header = ? LIMIT 1",
    (account_id, message_id),
  )
  row = await cursor.fetchone()
  if not row:
    return None
  return row["folder"], _row_to_parsed_email(row)


async def list_cached_emails(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
  limit: int = 50,
  offset: int = 0,
) -> list[ParsedEmail]:
  """List cached emails in a folder, ordered by date DESC."""
  cursor = await db.execute(
    "SELECT * FROM emails WHERE account_id = ? AND folder = ? ORDER BY date DESC LIMIT ? OFFSET ?",
    (account_id, folder, limit, offset),
  )
  rows = await cursor.fetchall()
  return [_row_to_parsed_email(r) for r in rows]


async def search_cached_emails(
  db: aiosqlite.Connection,
  account_id: str,
  query: str,
  folder: str | None = None,
  limit: int = 50,
) -> list[ParsedEmail]:
  """Search cached emails by subject, from, or body preview."""
  like_q = f"%{query}%"
  if folder:
    cursor = await db.execute(
      """SELECT * FROM emails WHERE account_id = ? AND folder = ?
               AND (subject LIKE ? OR from_addr LIKE ? OR from_name LIKE ? OR body_preview LIKE ?)
               ORDER BY date DESC LIMIT ?""",
      (account_id, folder, like_q, like_q, like_q, like_q, limit),
    )
  else:
    cursor = await db.execute(
      """SELECT * FROM emails WHERE account_id = ?
               AND (subject LIKE ? OR from_addr LIKE ? OR from_name LIKE ? OR body_preview LIKE ?)
               ORDER BY date DESC LIMIT ?""",
      (account_id, like_q, like_q, like_q, like_q, limit),
    )
  rows = await cursor.fetchall()
  return [_row_to_parsed_email(r) for r in rows]


async def get_thread_emails(
  db: aiosqlite.Connection,
  account_id: str,
  thread_id: str,
) -> list[ParsedEmail]:
  """Get all emails in a thread."""
  cursor = await db.execute(
    "SELECT * FROM emails WHERE account_id = ? AND thread_id = ? ORDER BY date ASC",
    (account_id, thread_id),
  )
  rows = await cursor.fetchall()
  return [_row_to_parsed_email(r) for r in rows]


async def count_emails(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
) -> int:
  """Count emails in a folder."""
  cursor = await db.execute(
    "SELECT COUNT(*) as cnt FROM emails WHERE account_id = ? AND folder = ?",
    (account_id, folder),
  )
  row = await cursor.fetchone()
  return row["cnt"] if row else 0


async def count_unread(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str | None = None,
) -> int:
  """Count unread emails, optionally in a specific folder."""
  if folder:
    cursor = await db.execute(
      "SELECT COUNT(*) as cnt FROM emails WHERE account_id = ? AND folder = ? AND is_read = 0",
      (account_id, folder),
    )
  else:
    cursor = await db.execute(
      "SELECT COUNT(*) as cnt FROM emails WHERE account_id = ? AND is_read = 0",
      (account_id,),
    )
  row = await cursor.fetchone()
  return row["cnt"] if row else 0


async def update_email_flags(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
  uid: int,
  **flags: bool,
) -> None:
  """Update flag columns on a cached email."""
  now = time.time()
  sets = []
  params: list[Any] = []
  for flag_name, flag_val in flags.items():
    if flag_name in ("is_read", "is_flagged", "is_answered", "is_draft"):
      sets.append(f"{flag_name} = ?")
      params.append(int(flag_val))
  if not sets:
    return
  sets.append("updated_at = ?")
  params.append(now)
  params.extend([account_id, folder, uid])
  await db.execute(
    f"UPDATE emails SET {', '.join(sets)} WHERE account_id = ? AND folder = ? AND uid = ?",
    params,
  )
  await db.commit()


async def delete_cached_email(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
  uid: int,
) -> None:
  """Delete a cached email."""
  await db.execute(
    "DELETE FROM emails WHERE account_id = ? AND folder = ? AND uid = ?",
    (account_id, folder, uid),
  )
  await db.commit()


async def move_cached_email(
  db: aiosqlite.Connection,
  account_id: str,
  source_folder: str,
  uid: int,
  dest_folder: str,
  new_uid: int,
) -> None:
  """Move a cached email from one folder to another."""
  now = time.time()
  await db.execute(
    """UPDATE emails SET folder = ?, uid = ?, updated_at = ?
           WHERE account_id = ? AND folder = ? AND uid = ?""",
    (dest_folder, new_uid, now, account_id, source_folder, uid),
  )
  await db.commit()


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


async def upsert_contact(
  db: aiosqlite.Connection,
  email_addr: str,
  display_name: str | None = None,
) -> None:
  """Insert or update a contact."""
  now = time.time()
  await db.execute(
    """
        INSERT INTO contacts (email, display_name, last_seen, message_count)
        VALUES (?, ?, ?, 1)
        ON CONFLICT (email) DO UPDATE SET
            display_name = COALESCE(excluded.display_name, contacts.display_name),
            last_seen = excluded.last_seen,
            message_count = contacts.message_count + 1
        """,
    (email_addr, display_name, now),
  )
  await db.commit()


async def search_contacts(
  db: aiosqlite.Connection,
  query: str,
  limit: int = 20,
) -> list[EmailContact]:
  """Search contacts by email or display name."""
  like_q = f"%{query}%"
  cursor = await db.execute(
    """SELECT * FROM contacts
           WHERE email LIKE ? OR display_name LIKE ?
           ORDER BY message_count DESC LIMIT ?""",
    (like_q, like_q, limit),
  )
  rows = await cursor.fetchall()
  return [
    EmailContact(
      email=r["email"],
      display_name=r["display_name"],
      last_seen=r["last_seen"],
      message_count=r["message_count"],
    )
    for r in rows
  ]


# ---------------------------------------------------------------------------
# Sync state
# ---------------------------------------------------------------------------


async def get_sync_state(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
) -> dict[str, Any] | None:
  """Get sync state for a folder."""
  cursor = await db.execute(
    "SELECT * FROM sync_state WHERE account_id = ? AND folder = ?",
    (account_id, folder),
  )
  row = await cursor.fetchone()
  if not row:
    return None
  return dict(row)


async def upsert_sync_state(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
  uidvalidity: int,
  last_seen_uid: int,
) -> None:
  """Update sync state for a folder."""
  now = time.time()
  await db.execute(
    """
        INSERT INTO sync_state (account_id, folder, uidvalidity, last_seen_uid, last_full_sync)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (account_id, folder) DO UPDATE SET
            uidvalidity = excluded.uidvalidity,
            last_seen_uid = excluded.last_seen_uid,
            last_full_sync = excluded.last_full_sync
        """,
    (account_id, folder, uidvalidity, last_seen_uid, now),
  )
  await db.commit()


async def clear_folder_cache(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
) -> None:
  """Clear cached emails for a folder (used when UIDVALIDITY changes)."""
  await db.execute(
    "DELETE FROM emails WHERE account_id = ? AND folder = ?",
    (account_id, folder),
  )
  await db.execute(
    "DELETE FROM sync_state WHERE account_id = ? AND folder = ?",
    (account_id, folder),
  )
  await db.commit()


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------


async def upsert_folder(
  db: aiosqlite.Connection,
  account_id: str,
  name: str,
  delimiter: str = "/",
  flags: list[str] | None = None,
  total_messages: int = 0,
  unseen_messages: int = 0,
  uidvalidity: int = 0,
  uidnext: int = 0,
) -> None:
  """Insert or update a folder."""
  now = time.time()
  await db.execute(
    """
        INSERT INTO folders (account_id, name, delimiter, flags, total_messages, unseen_messages,
                             uidvalidity, uidnext, last_synced, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (account_id, name) DO UPDATE SET
            delimiter = excluded.delimiter,
            flags = excluded.flags,
            total_messages = excluded.total_messages,
            unseen_messages = excluded.unseen_messages,
            uidvalidity = excluded.uidvalidity,
            uidnext = excluded.uidnext,
            last_synced = excluded.last_synced,
            updated_at = excluded.updated_at
        """,
    (
      account_id,
      name,
      delimiter,
      json.dumps(flags or []),
      total_messages,
      unseen_messages,
      uidvalidity,
      uidnext,
      now,
      now,
    ),
  )
  await db.commit()


async def list_folders(
  db: aiosqlite.Connection,
  account_id: str,
) -> list[dict[str, Any]]:
  """List all cached folders."""
  cursor = await db.execute(
    "SELECT * FROM folders WHERE account_id = ? ORDER BY name",
    (account_id,),
  )
  rows = await cursor.fetchall()
  return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


async def insert_summary(
  db: aiosqlite.Connection,
  summary_type: str,
  content: str,
  period_start: float,
  period_end: float,
) -> None:
  """Insert a summary record."""
  now = time.time()
  await db.execute(
    "INSERT INTO summaries (summary_type, content, period_start, period_end, created_at) VALUES (?, ?, ?, ?, ?)",
    (summary_type, content, period_start, period_end, now),
  )
  await db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_parsed_email(row: aiosqlite.Row) -> ParsedEmail:
  """Convert a database row to a ParsedEmail."""
  to_addrs = _parse_addr_list(row["to_addrs"])
  cc_addrs = _parse_addr_list(row["cc_addrs"])
  attachments = _parse_attachments(row["attachments_json"])
  references = _parse_string_list(row["references_header"])

  from_addr = None
  if row["from_addr"]:
    from_addr = EmailAddress(email=row["from_addr"], display_name=row["from_name"])

  return ParsedEmail(
    uid=row["uid"],
    message_id=row["message_id_header"] or "",
    in_reply_to=row["in_reply_to"],
    references=references,
    thread_id=row["thread_id"] or "",
    from_addr=from_addr,
    to_addrs=to_addrs,
    cc_addrs=cc_addrs,
    subject=row["subject"],
    date=row["date"],
    body_text=row["body_text"] or "",
    body_html=row["body_html"] or "",
    body_preview=row["body_preview"],
    is_read=bool(row["is_read"]),
    is_flagged=bool(row["is_flagged"]),
    is_answered=bool(row["is_answered"]),
    is_draft=bool(row["is_draft"]),
    has_attachments=bool(row["has_attachments"]),
    attachment_count=row["attachment_count"],
    attachments=attachments,
    raw_size=row["raw_size"],
  )


def _parse_addr_list(raw: str | None) -> list[EmailAddress]:
  if not raw:
    return []
  try:
    items = json.loads(raw)
    return [EmailAddress(**a) for a in items if isinstance(a, dict)]
  except (json.JSONDecodeError, TypeError):
    return []


def _parse_attachments(raw: str | None) -> list[EmailAttachment]:
  if not raw:
    return []
  try:
    items = json.loads(raw)
    return [EmailAttachment(**a) for a in items if isinstance(a, dict)]
  except (json.JSONDecodeError, TypeError):
    return []


def _parse_string_list(raw: str | None) -> list[str]:
  if not raw:
    return []
  try:
    items = json.loads(raw)
    return items if isinstance(items, list) else []
  except (json.JSONDecodeError, TypeError):
    return []
