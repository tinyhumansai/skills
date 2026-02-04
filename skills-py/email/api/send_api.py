"""
Email sending operations API (send, reply, forward via SMTP).
"""

from __future__ import annotations

import logging

from ..client.smtp_client import send_email as smtp_send
from .message_api import get_account_id, get_message

log = logging.getLogger("skill.email.api.send")


async def send_new_email(
  to: list[str],
  subject: str,
  body: str,
  html_body: str | None = None,
  cc: list[str] | None = None,
  bcc: list[str] | None = None,
  reply_to: str | None = None,
) -> bool:
  """Compose and send a new email."""
  return await smtp_send(
    to=to,
    subject=subject,
    body=body,
    html_body=html_body,
    cc=cc,
    bcc=bcc,
    reply_to=reply_to,
  )


async def reply_to_email(
  uid: int,
  body: str,
  folder: str = "INBOX",
  reply_all: bool = False,
  html_body: str | None = None,
) -> bool:
  """Reply to an email, preserving thread headers."""
  original = await get_message(uid, folder)
  if not original:
    raise RuntimeError(f"Original message UID {uid} not found in {folder}")

  # Build recipients
  to_addrs: list[str] = []
  cc_addrs: list[str] | None = None

  if original.from_addr:
    to_addrs.append(original.from_addr.email)

  if reply_all:
    account_id = get_account_id()
    # Add To and CC from original, excluding ourselves
    for addr in original.to_addrs:
      if addr.email.lower() != account_id.lower() and addr.email not in to_addrs:
        to_addrs.append(addr.email)
    cc_list = [
      addr.email
      for addr in original.cc_addrs
      if addr.email.lower() != account_id.lower() and addr.email not in to_addrs
    ]
    if cc_list:
      cc_addrs = cc_list

  # Build subject
  subject = original.subject
  if not subject.lower().startswith("re:"):
    subject = f"Re: {subject}"

  # Build references chain
  references = list(original.references)
  if original.message_id and original.message_id not in references:
    references.append(original.message_id)

  return await smtp_send(
    to=to_addrs,
    subject=subject,
    body=body,
    html_body=html_body,
    cc=cc_addrs,
    in_reply_to=original.message_id,
    references=references,
  )


async def forward_email(
  uid: int,
  to: list[str],
  folder: str = "INBOX",
  body: str | None = None,
  html_body: str | None = None,
) -> bool:
  """Forward an email to new recipients."""
  original = await get_message(uid, folder)
  if not original:
    raise RuntimeError(f"Original message UID {uid} not found in {folder}")

  # Build subject
  subject = original.subject
  if not subject.lower().startswith("fwd:"):
    subject = f"Fwd: {subject}"

  # Build forwarded body
  fwd_header = (
    f"\n\n---------- Forwarded message ----------\n"
    f"From: {original.from_addr.email if original.from_addr else 'Unknown'}\n"
    f"Subject: {original.subject}\n"
  )

  fwd_body = (body or "") + fwd_header + (original.body_text or original.body_preview)

  return await smtp_send(
    to=to,
    subject=subject,
    body=fwd_body,
    html_body=html_body,
  )
