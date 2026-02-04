"""
Incremental UID-based sync for IMAP folders.

Polling strategy:
1. NOOP keepalive
2. Check UIDVALIDITY — if changed, clear folder cache
3. UID SEARCH for new messages since last_seen_uid
4. Fetch envelope + flags in batches (not full body)
5. Update sync_state highwater marks
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..client.imap_client import get_imap_client
from ..state import store
from .queries import (
  clear_folder_cache,
  get_sync_state,
  upsert_contact,
  upsert_emails_batch,
  upsert_folder,
  upsert_sync_state,
)

if TYPE_CHECKING:
  import aiosqlite

log = logging.getLogger("skill.email.db.sync")

BATCH_SIZE = 50


async def sync_folder(
  db: aiosqlite.Connection,
  account_id: str,
  folder: str,
) -> int:
  """Incrementally sync a folder. Returns count of new messages."""
  client = get_imap_client()
  if not client or not client.is_connected:
    log.warning("IMAP client not connected, skipping sync for %s", folder)
    return 0

  try:
    # Select the folder
    status = await client.select_folder(folder)
    if not status:
      return 0

    uidvalidity = status.get("uidvalidity", 0)
    uidnext = status.get("uidnext", 0)
    total = status.get("exists", 0)
    unseen = status.get("unseen", 0)

    # Update folder status in DB
    await upsert_folder(
      db,
      account_id,
      folder,
      total_messages=total,
      unseen_messages=unseen,
      uidvalidity=uidvalidity,
      uidnext=uidnext,
    )

    # Check sync state
    sync_state = await get_sync_state(db, account_id, folder)
    last_uid = 0

    if sync_state:
      if sync_state["uidvalidity"] != uidvalidity and sync_state["uidvalidity"] != 0:
        log.warning("UIDVALIDITY changed for %s, clearing cache", folder)
        await clear_folder_cache(db, account_id, folder)
      else:
        last_uid = sync_state["last_seen_uid"]

    # Search for new messages
    new_uids = await client.search_uids_since(last_uid + 1)
    if not new_uids:
      await upsert_sync_state(db, account_id, folder, uidvalidity, last_uid)
      return 0

    log.info("Found %d new messages in %s", len(new_uids), folder)

    # Fetch in batches
    max_uid = last_uid
    total_fetched = 0

    for i in range(0, len(new_uids), BATCH_SIZE):
      batch = new_uids[i : i + BATCH_SIZE]
      emails = await client.fetch_envelopes(batch)
      if emails:
        await upsert_emails_batch(db, account_id, folder, emails)
        total_fetched += len(emails)

        # Extract contacts
        for email in emails:
          if email.from_addr:
            await upsert_contact(db, email.from_addr.email, email.from_addr.display_name)
          for addr in email.to_addrs:
            await upsert_contact(db, addr.email, addr.display_name)
          for addr in email.cc_addrs:
            await upsert_contact(db, addr.email, addr.display_name)

      batch_max = max(batch) if batch else 0
      if batch_max > max_uid:
        max_uid = batch_max

    # Update sync state
    await upsert_sync_state(db, account_id, folder, uidvalidity, max_uid)

    # Update folder in store
    from ..state.types import EmailFolder

    store.update_folder(
      folder,
      EmailFolder(
        name=folder,
        total_messages=total,
        unseen_messages=unseen,
        uidvalidity=uidvalidity,
        uidnext=uidnext,
      ),
    )

    return total_fetched

  except Exception:
    log.exception("Error syncing folder %s", folder)
    return 0


async def sync_all_watched_folders(
  db: aiosqlite.Connection,
  account_id: str,
  folders: list[str] | None = None,
) -> dict[str, int]:
  """Sync all watched folders. Returns {folder: new_count}."""
  if folders is None:
    folders = ["INBOX"]

  results: dict[str, int] = {}
  for folder in folders:
    count = await sync_folder(db, account_id, folder)
    results[folder] = count

  return results


async def refresh_folder_list(
  db: aiosqlite.Connection,
  account_id: str,
) -> list[str]:
  """Refresh the list of folders from the IMAP server."""
  client = get_imap_client()
  if not client or not client.is_connected:
    return []

  try:
    folders = await client.list_folders()
    from ..state.types import EmailFolder

    folder_dict: dict[str, EmailFolder] = {}

    for f in folders:
      name = f["name"]
      await upsert_folder(db, account_id, name, delimiter=f.get("delimiter", "/"))
      flags_val: str | list[str] | None = f.get("flags", [])
      flags_list: list[str] = (
        flags_val
        if isinstance(flags_val, list)
        else [flags_val]
        if isinstance(flags_val, str)
        else []
      )
      folder_dict[name] = EmailFolder(
        name=name,
        delimiter=f.get("delimiter", "/"),
        flags=flags_list,
      )

    store.set_folders(folder_dict)
    return list(folder_dict.keys())

  except Exception:
    log.exception("Error refreshing folder list")
    return []
