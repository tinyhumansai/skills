"""
Email flag/manage operations API (mark read, flag, move, delete, archive).
"""

from __future__ import annotations

import logging

from ..client.imap_client import get_imap_client
from ..db.connection import get_db
from ..db.queries import delete_cached_email, update_email_flags

log = logging.getLogger("skill.email.api.flag")

_account_id: str = ""


def set_account_id(account_id: str) -> None:
  global _account_id
  _account_id = account_id


async def _ensure_folder(folder: str) -> None:
  """Select the folder on the IMAP client."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    raise RuntimeError("IMAP not connected")
  await client.select_folder(folder)


async def mark_read(uids: list[int], folder: str = "INBOX") -> bool:
  """Mark messages as read (set \\Seen flag)."""
  await _ensure_folder(folder)
  client = get_imap_client()
  if not client:
    return False

  result = await client.store_flags(uids, r"(\Seen)", "+FLAGS")
  if result:
    db = await get_db()
    for uid in uids:
      await update_email_flags(db, _account_id, folder, uid, is_read=True)
  return result


async def mark_unread(uids: list[int], folder: str = "INBOX") -> bool:
  """Mark messages as unread (remove \\Seen flag)."""
  await _ensure_folder(folder)
  client = get_imap_client()
  if not client:
    return False

  result = await client.store_flags(uids, r"(\Seen)", "-FLAGS")
  if result:
    db = await get_db()
    for uid in uids:
      await update_email_flags(db, _account_id, folder, uid, is_read=False)
  return result


async def flag_message(uids: list[int], folder: str = "INBOX") -> bool:
  """Star/flag messages (set \\Flagged flag)."""
  await _ensure_folder(folder)
  client = get_imap_client()
  if not client:
    return False

  result = await client.store_flags(uids, r"(\Flagged)", "+FLAGS")
  if result:
    db = await get_db()
    for uid in uids:
      await update_email_flags(db, _account_id, folder, uid, is_flagged=True)
  return result


async def unflag_message(uids: list[int], folder: str = "INBOX") -> bool:
  """Remove star/flag from messages."""
  await _ensure_folder(folder)
  client = get_imap_client()
  if not client:
    return False

  result = await client.store_flags(uids, r"(\Flagged)", "-FLAGS")
  if result:
    db = await get_db()
    for uid in uids:
      await update_email_flags(db, _account_id, folder, uid, is_flagged=False)
  return result


async def delete_message(uids: list[int], folder: str = "INBOX") -> bool:
  """Move messages to Trash (or set \\Deleted + expunge)."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    return False

  await client.select_folder(folder)

  # Try to move to Trash first
  trash_folders = ["[Gmail]/Trash", "Trash", "Deleted Items", "Deleted"]
  moved = False
  for trash in trash_folders:
    if await client.copy_messages(uids, trash):
      await client.store_flags(uids, r"(\Deleted)", "+FLAGS")
      await client.expunge()
      moved = True
      break

  if not moved:
    # Fall back to just deleting
    await client.store_flags(uids, r"(\Deleted)", "+FLAGS")
    await client.expunge()

  # Update cache
  db = await get_db()
  for uid in uids:
    await delete_cached_email(db, _account_id, folder, uid)

  return True


async def move_message(
  uids: list[int],
  destination: str,
  folder: str = "INBOX",
) -> bool:
  """Move messages to another folder."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    return False

  await client.select_folder(folder)
  result = await client.move_messages(uids, destination)
  if result:
    await client.expunge()
    db = await get_db()
    for uid in uids:
      await delete_cached_email(db, _account_id, folder, uid)

  return result


async def archive_message(uids: list[int], folder: str = "INBOX") -> bool:
  """Move messages to Archive."""
  archive_folders = ["[Gmail]/All Mail", "Archive", "All Mail"]

  client = get_imap_client()
  if not client or not await client.ensure_connected():
    return False

  await client.select_folder(folder)

  for archive in archive_folders:
    if await client.copy_messages(uids, archive):
      await client.store_flags(uids, r"(\Deleted)", "+FLAGS")
      await client.expunge()

      db = await get_db()
      for uid in uids:
        await delete_cached_email(db, _account_id, folder, uid)
      return True

  raise RuntimeError("Could not find Archive folder")
