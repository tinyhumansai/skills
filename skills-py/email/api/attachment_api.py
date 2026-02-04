"""
Email attachment operations API.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from ..client.imap_client import get_imap_client
from ..db.connection import get_db
from ..db.queries import get_cached_email

if TYPE_CHECKING:
  from ..state.types import EmailAttachment

log = logging.getLogger("skill.email.api.attachment")

_account_id: str = ""
_data_dir: str = ""


def set_account_id(account_id: str) -> None:
  global _account_id
  _account_id = account_id


def set_data_dir(data_dir: str) -> None:
  global _data_dir
  _data_dir = data_dir


async def list_attachments(
  uid: int,
  folder: str = "INBOX",
) -> list[EmailAttachment]:
  """List attachments on a message."""
  db = await get_db()
  cached = await get_cached_email(db, _account_id, folder, uid)
  if cached and cached.attachments:
    return cached.attachments

  # Fetch full message if not cached
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    return cached.attachments if cached else []

  await client.select_folder(folder)
  full = await client.fetch_full_message(uid)
  return full.attachments if full else []


async def get_attachment_info(
  uid: int,
  attachment_index: int,
  folder: str = "INBOX",
) -> EmailAttachment | None:
  """Get metadata for a specific attachment."""
  attachments = await list_attachments(uid, folder)
  for att in attachments:
    if att.index == attachment_index:
      return att
  return None


async def save_attachment(
  uid: int,
  attachment_index: int,
  folder: str = "INBOX",
  filename: str | None = None,
) -> str | None:
  """Save an attachment to the skill's data directory.

  Returns the file path on success, None on failure.
  """
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    raise RuntimeError("IMAP not connected")

  await client.select_folder(folder)

  # Fetch full RFC822 message
  response = await client._imap.uid("fetch", str(uid), "(RFC822)")
  if response.result != "OK":
    raise RuntimeError(f"Failed to fetch message UID {uid}")

  # Find raw bytes
  raw_bytes: bytes | None = None
  for line in response.lines:
    if isinstance(line, bytes):
      raw_bytes = line
      break

  if not raw_bytes:
    raise RuntimeError("No message body found")

  # Parse and extract the attachment
  import email as email_lib
  import email.policy

  msg = email_lib.message_from_bytes(raw_bytes, policy=email_lib.policy.default)

  att_count = 0
  for part in msg.walk():
    disposition = str(part.get("Content-Disposition", ""))
    content_type = part.get_content_type()

    if "attachment" in disposition.lower() or (
      content_type
      not in (
        "text/plain",
        "text/html",
        "multipart/alternative",
        "multipart/mixed",
        "multipart/related",
      )
      and disposition
    ):
      if att_count == attachment_index:
        # Found it
        att_filename = filename or part.get_filename() or f"attachment_{attachment_index}"
        payload = part.get_payload(decode=True)
        if not payload:
          raise RuntimeError("Attachment has no content")

        # Save to data dir
        save_dir = os.path.join(_data_dir, "attachments")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, att_filename)

        with open(save_path, "wb") as f:
          f.write(payload)

        log.info("Saved attachment to %s (%d bytes)", save_path, len(payload))
        return save_path

      att_count += 1

  raise RuntimeError(f"Attachment index {attachment_index} not found")
