"""
Email message read/search operations API.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from ..client.imap_client import get_imap_client
from ..db.connection import get_db
from ..db.queries import (
  count_emails,
  count_unread,
  get_cached_email,
  get_thread_emails,
  list_cached_emails,
  search_cached_emails,
  upsert_contact,
  upsert_email,
)

if TYPE_CHECKING:
  from ..state.types import ParsedEmail

log = logging.getLogger("skill.email.api.message")

# Account ID is the email address — set during load
_account_id: str = ""


def set_account_id(account_id: str) -> None:
  global _account_id
  _account_id = account_id


def get_account_id() -> str:
  return _account_id


async def list_messages(
  folder: str = "INBOX",
  limit: int = 20,
  offset: int = 0,
) -> list[ParsedEmail]:
  """List messages in a folder. Uses cache, falls back to IMAP."""
  db = await get_db()

  # Try cache first
  cached = await list_cached_emails(db, _account_id, folder, limit, offset)
  if cached:
    return cached

  # If cache is empty, do a quick fetch
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    return []

  status = await client.select_folder(folder)
  if not status:
    return []

  # Search recent UIDs
  uids = await client.search_messages("ALL")
  if not uids:
    return []

  # Take last `limit + offset` UIDs (most recent)
  relevant_uids = uids[-(limit + offset) :]
  if offset:
    relevant_uids = relevant_uids[:limit]

  emails = await client.fetch_envelopes(relevant_uids)
  if emails:
    for email_obj in emails:
      await upsert_email(db, _account_id, folder, email_obj)
      if email_obj.from_addr:
        await upsert_contact(db, email_obj.from_addr.email, email_obj.from_addr.display_name)

  return emails


async def get_message(
  uid: int,
  folder: str = "INBOX",
  format: str = "text",
) -> ParsedEmail | None:
  """Get full message content. Fetches body on-demand if not cached."""
  db = await get_db()

  # Check cache
  cached = await get_cached_email(db, _account_id, folder, uid)
  if cached and (cached.body_text or cached.body_html):
    return cached

  # Fetch full message from IMAP
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    return cached  # Return headers-only if we have them

  await client.select_folder(folder)
  full_email = await client.fetch_full_message(uid)
  if full_email:
    await upsert_email(db, _account_id, folder, full_email)
    if full_email.from_addr:
      await upsert_contact(db, full_email.from_addr.email, full_email.from_addr.display_name)
    return full_email

  return cached


async def search_messages(
  query: str,
  folder: str | None = None,
  limit: int = 20,
  from_addr: str | None = None,
  to_addr: str | None = None,
  subject: str | None = None,
  since: str | None = None,
  before: str | None = None,
  has_attachment: bool | None = None,
) -> list[ParsedEmail]:
  """Search messages using IMAP criteria."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    # Fall back to cached search
    db = await get_db()
    return await search_cached_emails(db, _account_id, query, folder, limit)

  # Build IMAP search criteria
  criteria_parts: list[str] = []
  if query:
    criteria_parts.append(f'TEXT "{query}"')
  if from_addr:
    criteria_parts.append(f'FROM "{from_addr}"')
  if to_addr:
    criteria_parts.append(f'TO "{to_addr}"')
  if subject:
    criteria_parts.append(f'SUBJECT "{subject}"')
  if since:
    criteria_parts.append(f"SINCE {since}")
  if before:
    criteria_parts.append(f"BEFORE {before}")
  if has_attachment:
    # IMAP doesn't have a direct attachment search; approximate with size
    criteria_parts.append("LARGER 10000")

  criteria = " ".join(criteria_parts) if criteria_parts else "ALL"

  if folder:
    await client.select_folder(folder)
  else:
    await client.select_folder("INBOX")

  uids = await client.search_messages(criteria)
  if not uids:
    return []

  # Take most recent up to limit
  uids = uids[-limit:]
  emails = await client.fetch_envelopes(uids)

  # Cache results
  db = await get_db()
  target_folder = folder or "INBOX"
  for email_obj in emails:
    await upsert_email(db, _account_id, target_folder, email_obj)

  return emails


async def get_unread_messages(
  folder: str = "INBOX",
  limit: int = 20,
) -> list[ParsedEmail]:
  """Get unread messages in a folder."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    db = await get_db()
    cached = await list_cached_emails(db, _account_id, folder, limit)
    return [e for e in cached if not e.is_read]

  await client.select_folder(folder)
  uids = await client.search_messages("UNSEEN")
  if not uids:
    return []

  uids = uids[-limit:]
  return await client.fetch_envelopes(uids)


async def get_thread(
  message_id: int,
  folder: str = "INBOX",
) -> list[ParsedEmail]:
  """Get all messages in a thread."""
  db = await get_db()

  # First, get the message to find its thread_id
  msg = await get_cached_email(db, _account_id, folder, message_id)
  if not msg or not msg.thread_id:
    return [msg] if msg else []

  return await get_thread_emails(db, _account_id, msg.thread_id)


async def count_folder_messages(folder: str = "INBOX") -> int:
  """Count messages in a folder."""
  db = await get_db()
  return await count_emails(db, _account_id, folder)


async def get_unread_count(folder: str | None = None) -> int:
  """Get unread count for a folder or all folders."""
  db = await get_db()
  return await count_unread(db, _account_id, folder)


async def get_recent_messages(
  hours: int = 24,
  folder: str = "INBOX",
  limit: int = 20,
) -> list[ParsedEmail]:
  """Get messages from the last N hours."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    db = await get_db()
    all_msgs = await list_cached_emails(db, _account_id, folder, limit * 2)
    cutoff = time.time() - (hours * 3600)
    return [m for m in all_msgs if m.date >= cutoff][:limit]

  await client.select_folder(folder)

  # IMAP SINCE uses date only (not time), so we search a bit broader
  import datetime

  since_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=hours)
  since_str = since_date.strftime("%d-%b-%Y")

  uids = await client.search_messages(f"SINCE {since_str}")
  if not uids:
    return []

  uids = uids[-limit:]
  return await client.fetch_envelopes(uids)
