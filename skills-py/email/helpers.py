"""
Shared formatting and error handling helpers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
  from .state.types import EmailAddress, EmailFolder, ParsedEmail

log = logging.getLogger("skill.email.helpers")


# ---------------------------------------------------------------------------
# Tool result
# ---------------------------------------------------------------------------


@dataclass
class ToolResult:
  content: str
  is_error: bool = False


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_email_summary(email: ParsedEmail) -> str:
  """Format a single email as a summary line."""
  from_str = ""
  if email.from_addr:
    from_str = email.from_addr.display_name or email.from_addr.email
  date_str = ""
  if email.date:
    date_str = datetime.fromtimestamp(email.date, tz=UTC).strftime("%Y-%m-%d %H:%M")
  read_flag = "" if email.is_read else "[UNREAD] "
  flag_flag = "[*] " if email.is_flagged else ""
  attach_flag = " [+att]" if email.has_attachments else ""

  return f"{read_flag}{flag_flag}UID:{email.uid} | {date_str} | From: {from_str} | Subject: {email.subject}{attach_flag}"


def format_email_detail(email: ParsedEmail) -> str:
  """Format a full email for display."""
  lines = []

  lines.append(f"UID: {email.uid}")
  if email.message_id:
    lines.append(f"Message-ID: {email.message_id}")
  if email.from_addr:
    from_str = email.from_addr.display_name or email.from_addr.email
    lines.append(f"From: {from_str} <{email.from_addr.email}>")
  if email.to_addrs:
    to_str = ", ".join(a.display_name or a.email for a in email.to_addrs)
    lines.append(f"To: {to_str}")
  if email.cc_addrs:
    cc_str = ", ".join(a.display_name or a.email for a in email.cc_addrs)
    lines.append(f"CC: {cc_str}")
  lines.append(f"Subject: {email.subject}")
  if email.date:
    lines.append(f"Date: {datetime.fromtimestamp(email.date, tz=UTC).isoformat()}")

  flags = []
  if not email.is_read:
    flags.append("UNREAD")
  if email.is_flagged:
    flags.append("FLAGGED")
  if email.is_answered:
    flags.append("ANSWERED")
  if email.is_draft:
    flags.append("DRAFT")
  if flags:
    lines.append(f"Flags: {', '.join(flags)}")

  if email.has_attachments:
    lines.append(f"Attachments: {email.attachment_count}")
    for att in email.attachments:
      size_str = _format_size(att.size)
      lines.append(f"  [{att.index}] {att.filename} ({att.content_type}, {size_str})")

  if email.thread_id and email.thread_id != email.message_id:
    lines.append(f"Thread-ID: {email.thread_id}")

  lines.append("")
  if email.body_text:
    lines.append(email.body_text)
  elif email.body_preview:
    lines.append(f"[Preview] {email.body_preview}")

  return "\n".join(lines)


def format_folder(folder: EmailFolder) -> str:
  """Format folder info."""
  unseen = f" ({folder.unseen_messages} unread)" if folder.unseen_messages else ""
  return f"{folder.name}: {folder.total_messages} messages{unseen}"


def format_address(addr: EmailAddress) -> str:
  """Format an email address for display."""
  if addr.display_name:
    return f"{addr.display_name} <{addr.email}>"
  return addr.email


def _format_size(size: int) -> str:
  """Format byte size for display."""
  if size < 1024:
    return f"{size} B"
  if size < 1024 * 1024:
    return f"{size / 1024:.1f} KB"
  return f"{size / (1024 * 1024):.1f} MB"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class ErrorCategory(str, Enum):
  FOLDER = "FOLDER"
  MSG = "MSG"
  SEND = "SEND"
  FLAG = "FLAG"
  ATTACH = "ATTACH"
  ACCOUNT = "ACCOUNT"
  DRAFT = "DRAFT"
  SEARCH = "SEARCH"
  VALIDATION = "VALIDATION"
  AUTH = "AUTH"
  SYNC = "SYNC"


def log_and_format_error(
  function_name: str,
  error: Exception,
  category: str | ErrorCategory | None = None,
) -> ToolResult:
  prefix = category.value if isinstance(category, ErrorCategory) else (category or "GEN")
  hash_val = sum(ord(c) for c in function_name) % 1000
  error_code = f"{prefix}-ERR-{hash_val:03d}"

  log.error("[MCP] Error in %s - Code: %s - %s", function_name, error_code, error)

  from .validation import ValidationError

  if isinstance(error, ValidationError):
    user_message = str(error)
  else:
    user_message = f"An error occurred (code: {error_code}). Check logs for details."

  return ToolResult(content=user_message, is_error=True)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

ToolTier = Literal["state_only", "api_read", "api_write"]

_RATE_LIMIT = {
  "API_READ_DELAY_MS": 500,
  "API_WRITE_DELAY_MS": 1000,
  "MAX_CALLS_PER_MINUTE": 30,
}

_last_call_time: float = 0
_call_history: deque[float] = deque()


def _purge_old(now_ms: float) -> None:
  cutoff = now_ms - 60_000
  while _call_history and _call_history[0] < cutoff:
    _call_history.popleft()


async def enforce_rate_limit(tier: ToolTier) -> None:
  global _last_call_time

  if tier == "state_only":
    return

  now_ms = time.time() * 1000
  _purge_old(now_ms)

  if len(_call_history) >= _RATE_LIMIT["MAX_CALLS_PER_MINUTE"]:
    oldest = _call_history[0]
    wait_ms = oldest + 60_000 - now_ms + 50
    if wait_ms > 0:
      await asyncio.sleep(wait_ms / 1000)
    _purge_old(time.time() * 1000)

  required_delay = (
    _RATE_LIMIT["API_WRITE_DELAY_MS"] if tier == "api_write" else _RATE_LIMIT["API_READ_DELAY_MS"]
  )

  now_ms = time.time() * 1000
  elapsed = now_ms - _last_call_time
  if elapsed < required_delay:
    await asyncio.sleep((required_delay - elapsed) / 1000)

  _last_call_time = time.time() * 1000
  _call_history.append(_last_call_time)
