"""
Email MIME parsing utilities.

Uses stdlib email.parser for RFC822 parsing.
"""

from __future__ import annotations

import email
import email.policy
import email.utils
import logging
import re
import time
from email.parser import BytesParser
from typing import Any

from ..state.types import EmailAddress, EmailAttachment, ParsedEmail

log = logging.getLogger("skill.email.client.parsers")

_parser = BytesParser(policy=email.policy.default)

# Maximum HTML body size to store (100 KB)
MAX_HTML_SIZE = 100_000
# Preview length
PREVIEW_LENGTH = 200


def parse_raw_email(raw: bytes, uid: int) -> ParsedEmail:
  """Parse a raw RFC822 email into a ParsedEmail."""
  msg = _parser.parsebytes(raw)

  # From
  from_addr = _parse_address(msg.get("From", ""))

  # To, CC, BCC
  to_addrs = _parse_address_list(msg.get("To", ""))
  cc_addrs = _parse_address_list(msg.get("Cc", ""))
  bcc_addrs = _parse_address_list(msg.get("Bcc", ""))

  # Message-ID and threading
  message_id = msg.get("Message-ID", "").strip()
  in_reply_to = msg.get("In-Reply-To", "")
  in_reply_to = in_reply_to.strip() if in_reply_to else None
  references = _parse_references(msg.get("References", ""))
  thread_id = _compute_thread_id(message_id, references)

  # Subject
  subject = msg.get("Subject", "")

  # Date
  date_str = msg.get("Date", "")
  date_ts = _parse_date(date_str)

  # Flags (will be set by caller from IMAP flags)
  is_read = False
  is_flagged = False
  is_answered = False
  is_draft = False

  # Body
  body_text = ""
  body_html = ""
  attachments: list[EmailAttachment] = []
  att_index = 0

  if msg.is_multipart():
    for part in msg.walk():
      content_type = part.get_content_type()
      disposition = str(part.get("Content-Disposition", ""))

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
        # Attachment
        filename = part.get_filename() or f"attachment_{att_index}"
        size = len(part.get_payload(decode=True) or b"")
        attachments.append(
          EmailAttachment(
            index=att_index,
            filename=filename,
            content_type=content_type,
            size=size,
          )
        )
        att_index += 1
      elif content_type == "text/plain" and not body_text:
        payload = part.get_payload(decode=True)
        if payload and isinstance(payload, bytes):
          charset = part.get_content_charset() or "utf-8"
          try:
            body_text = payload.decode(charset, errors="replace")
          except (LookupError, UnicodeDecodeError):
            body_text = payload.decode("utf-8", errors="replace")
      elif content_type == "text/html" and not body_html:
        payload = part.get_payload(decode=True)
        if payload and isinstance(payload, bytes):
          charset = part.get_content_charset() or "utf-8"
          try:
            body_html = payload.decode(charset, errors="replace")
          except (LookupError, UnicodeDecodeError):
            body_html = payload.decode("utf-8", errors="replace")
  else:
    content_type = msg.get_content_type()
    payload = msg.get_payload(decode=True)
    if payload and isinstance(payload, bytes):
      charset = msg.get_content_charset() or "utf-8"
      try:
        decoded = payload.decode(charset, errors="replace")
      except (LookupError, UnicodeDecodeError):
        decoded = payload.decode("utf-8", errors="replace")
      if content_type == "text/html":
        body_html = decoded
      else:
        body_text = decoded

  # Truncate HTML
  if len(body_html) > MAX_HTML_SIZE:
    body_html = body_html[:MAX_HTML_SIZE]

  # Preview
  preview_source = body_text or _strip_html(body_html)
  body_preview = preview_source[:PREVIEW_LENGTH].replace("\n", " ").strip()

  return ParsedEmail(
    uid=uid,
    message_id=message_id,
    in_reply_to=in_reply_to,
    references=references,
    thread_id=thread_id,
    from_addr=from_addr,
    to_addrs=to_addrs,
    cc_addrs=cc_addrs,
    bcc_addrs=bcc_addrs,
    subject=subject,
    date=date_ts,
    body_text=body_text,
    body_html=body_html,
    body_preview=body_preview,
    is_read=is_read,
    is_flagged=is_flagged,
    is_answered=is_answered,
    is_draft=is_draft,
    has_attachments=len(attachments) > 0,
    attachment_count=len(attachments),
    attachments=attachments,
    raw_size=len(raw),
  )


def parse_fetch_response(lines: list[Any], uids: list[int]) -> list[ParsedEmail]:
  """Parse a FETCH response for envelope + flags data.

  This is a best-effort parser for the structured FETCH response.
  Different IMAP servers format responses differently, so we extract
  what we can from the response lines.
  """
  results: list[ParsedEmail] = []

  # Try to extract basic info from fetch response lines
  current_uid: int | None = None
  current_flags: list[str] = []
  current_size: int = 0
  current_subject: str = ""
  current_from: str = ""
  current_date_str: str = ""
  current_message_id: str = ""
  current_in_reply_to: str = ""

  for line in lines:
    if not isinstance(line, str) or not line.strip():
      continue

    line_str = line.strip()

    # Extract UID
    uid_match = re.search(r"UID\s+(\d+)", line_str)
    if uid_match:
      if current_uid is not None:
        # Save previous message
        results.append(
          _build_envelope_email(
            current_uid,
            current_flags,
            current_size,
            current_subject,
            current_from,
            current_date_str,
            current_message_id,
            current_in_reply_to,
          )
        )
      current_uid = int(uid_match.group(1))
      current_flags = []
      current_size = 0
      current_subject = ""
      current_from = ""
      current_date_str = ""
      current_message_id = ""
      current_in_reply_to = ""

    # Extract FLAGS
    flags_match = re.search(r"FLAGS\s*\(([^)]*)\)", line_str)
    if flags_match:
      current_flags = flags_match.group(1).split()

    # Extract size
    size_match = re.search(r"RFC822\.SIZE\s+(\d+)", line_str)
    if size_match:
      current_size = int(size_match.group(1))

  # Don't forget the last one
  if current_uid is not None:
    results.append(
      _build_envelope_email(
        current_uid,
        current_flags,
        current_size,
        current_subject,
        current_from,
        current_date_str,
        current_message_id,
        current_in_reply_to,
      )
    )

  # If we couldn't parse structured response, create stubs for known UIDs
  parsed_uids = {e.uid for e in results}
  for uid in uids:
    if uid not in parsed_uids:
      results.append(ParsedEmail(uid=uid))

  return results


def parse_full_message(lines: list[Any], uid: int) -> ParsedEmail | None:
  """Parse a FETCH RFC822 response into a full ParsedEmail."""
  raw_bytes: bytes | None = None
  flags: list[str] = []

  for line in lines:
    if isinstance(line, bytes):
      raw_bytes = line
    elif isinstance(line, str):
      flags_match = re.search(r"FLAGS\s*\(([^)]*)\)", line)
      if flags_match:
        flags = flags_match.group(1).split()

  if raw_bytes is None:
    return None

  email_obj = parse_raw_email(raw_bytes, uid)
  # Apply flags
  email_obj.is_read = r"\Seen" in flags
  email_obj.is_flagged = r"\Flagged" in flags
  email_obj.is_answered = r"\Answered" in flags
  email_obj.is_draft = r"\Draft" in flags

  return email_obj


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_address(raw: str) -> EmailAddress | None:
  """Parse a single email address."""
  if not raw:
    return None
  name, addr = email.utils.parseaddr(raw)
  if not addr:
    return None
  return EmailAddress(
    email=addr,
    display_name=name if name else None,
  )


def _parse_address_list(raw: str) -> list[EmailAddress]:
  """Parse a comma-separated list of email addresses."""
  if not raw:
    return []
  addrs = email.utils.getaddresses([raw])
  result = []
  for name, addr in addrs:
    if addr:
      result.append(
        EmailAddress(
          email=addr,
          display_name=name if name else None,
        )
      )
  return result


def _parse_references(raw: str | None) -> list[str]:
  """Parse the References header into a list of Message-IDs."""
  if not raw:
    return []
  return [r.strip() for r in re.findall(r"<[^>]+>", raw)]


def _compute_thread_id(message_id: str, references: list[str]) -> str:
  """Compute thread ID from the first Message-ID in the References chain.

  Per simplified RFC 5256: thread_id is the first message in the chain.
  """
  if references:
    return references[0]
  return message_id


def _parse_date(date_str: str) -> float:
  """Parse an email date string to Unix timestamp."""
  if not date_str:
    return time.time()
  try:
    parsed = email.utils.parsedate_to_datetime(date_str)
    return parsed.timestamp()
  except (ValueError, TypeError):
    return time.time()


def _strip_html(html: str) -> str:
  """Simple HTML tag stripper for preview generation."""
  if not html:
    return ""
  text = re.sub(r"<[^>]+>", "", html)
  text = re.sub(r"\s+", " ", text)
  return text.strip()


def _build_envelope_email(
  uid: int,
  flags: list[str],
  size: int,
  subject: str,
  from_str: str,
  date_str: str,
  message_id: str,
  in_reply_to: str,
) -> ParsedEmail:
  """Build a ParsedEmail from envelope data."""
  from_addr = _parse_address(from_str) if from_str else None
  references = _parse_references(in_reply_to)
  thread_id = _compute_thread_id(message_id, references)

  return ParsedEmail(
    uid=uid,
    message_id=message_id,
    in_reply_to=in_reply_to if in_reply_to else None,
    references=references,
    thread_id=thread_id,
    from_addr=from_addr,
    subject=subject,
    date=_parse_date(date_str) if date_str else 0,
    is_read=r"\Seen" in flags,
    is_flagged=r"\Flagged" in flags,
    is_answered=r"\Answered" in flags,
    is_draft=r"\Draft" in flags,
    raw_size=size,
  )
