"""
Draft email operations API.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..client.imap_client import get_imap_client

if TYPE_CHECKING:
  from email.mime.multipart import MIMEMultipart
  from email.mime.text import MIMEText

  from ..state.types import ParsedEmail

log = logging.getLogger("skill.email.api.draft")

_account_id: str = ""

# Common draft folder names across providers
DRAFT_FOLDERS = ["[Gmail]/Drafts", "Drafts", "Draft", "INBOX.Drafts"]


def set_account_id(account_id: str) -> None:
  global _account_id
  _account_id = account_id


async def _find_drafts_folder() -> str:
  """Find the drafts folder name for this account."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    return "Drafts"

  folders = await client.list_folders()
  folder_names = [f["name"] for f in folders]

  for candidate in DRAFT_FOLDERS:
    if candidate in folder_names:
      return candidate

  # Default fallback
  return "Drafts"


async def save_draft(
  to: list[str],
  subject: str,
  body: str,
  html_body: str | None = None,
  cc: list[str] | None = None,
  bcc: list[str] | None = None,
) -> bool:
  """Save a draft to the Drafts folder."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    raise RuntimeError("IMAP not connected")

  # Build the MIME message
  from email.mime.multipart import MIMEMultipart
  from email.mime.text import MIMEText

  if html_body:
    msg: MIMEMultipart | MIMEText = MIMEMultipart("alternative")
    msg.attach(MIMEText(body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
  else:
    msg = MIMEText(body, "plain", "utf-8")

  msg["From"] = _account_id
  msg["To"] = ", ".join(to)
  msg["Subject"] = subject
  if cc:
    msg["Cc"] = ", ".join(cc)

  drafts_folder = await _find_drafts_folder()
  raw = msg.as_bytes()

  return await client.append_message(drafts_folder, raw, r"(\Draft \Seen)")


async def list_drafts(limit: int = 20) -> list[ParsedEmail]:
  """List draft messages."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    return []

  drafts_folder = await _find_drafts_folder()
  await client.select_folder(drafts_folder)

  uids = await client.search_messages("ALL")
  if not uids:
    return []

  uids = uids[-limit:]
  return await client.fetch_envelopes(uids)


async def update_draft(
  uid: int,
  to: list[str] | None = None,
  subject: str | None = None,
  body: str | None = None,
  html_body: str | None = None,
) -> bool:
  """Update an existing draft (delete old + save new)."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    raise RuntimeError("IMAP not connected")

  drafts_folder = await _find_drafts_folder()

  # Fetch the existing draft to get current values
  await client.select_folder(drafts_folder)
  existing = await client.fetch_full_message(uid)

  # Merge values
  final_to = to or [a.email for a in existing.to_addrs] if existing else to or []
  final_subject = subject or (existing.subject if existing else "")
  final_body = body or (existing.body_text if existing else "")
  final_html = html_body or (existing.body_html if existing else None)

  # Delete the old draft
  await client.store_flags([uid], r"(\Deleted)", "+FLAGS")
  await client.expunge()

  # Save the new draft
  return await save_draft(final_to, final_subject, final_body, final_html)


async def delete_draft(uid: int) -> bool:
  """Delete a draft."""
  client = get_imap_client()
  if not client or not await client.ensure_connected():
    raise RuntimeError("IMAP not connected")

  drafts_folder = await _find_drafts_folder()
  await client.select_folder(drafts_folder)

  result = await client.store_flags([uid], r"(\Deleted)", "+FLAGS")
  if result:
    await client.expunge()
  return result
