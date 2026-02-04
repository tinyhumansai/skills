"""
Shared formatting and error handling helpers.

Ported from helpers.ts.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from .state.types import TelegramChat, TelegramMessage, TelegramUser

log = logging.getLogger("skill.telegram.helpers")


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


@dataclass
class FormattedEntity:
  id: str
  name: str
  type: str
  username: str | None = None
  phone: str | None = None


@dataclass
class FormattedMessage:
  id: str | int
  date: str
  text: str
  from_id: str | None = None
  has_media: bool = False
  media_type: str | None = None


def format_entity(entity: TelegramChat | TelegramUser) -> FormattedEntity:
  if isinstance(entity, TelegramChat):
    chat_type = entity.type
    if chat_type == "supergroup":
      chat_type = "group"
    return FormattedEntity(
      id=entity.id,
      name=entity.title or "Unknown",
      type=chat_type,
      username=entity.username,
    )
  # TelegramUser
  parts = [entity.first_name or ""]
  if entity.last_name:
    parts.append(entity.last_name)
  name = " ".join(p for p in parts if p) or "Unknown"
  return FormattedEntity(
    id=entity.id,
    name=name,
    type="user",
    username=entity.username,
    phone=entity.phone_number,
  )


def format_message(message: TelegramMessage) -> FormattedMessage:
  result = FormattedMessage(
    id=message.id,
    date=datetime.fromtimestamp(message.date, tz=UTC).isoformat() if message.date else "",
    text=message.message or "",
  )
  if message.from_id:
    result.from_id = message.from_id
  if message.media and message.media.get("type"):
    result.has_media = True
    result.media_type = message.media["type"]
  return result


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class ErrorCategory(str, Enum):
  CHAT = "CHAT"
  MSG = "MSG"
  CONTACT = "CONTACT"
  GROUP = "GROUP"
  MEDIA = "MEDIA"
  PROFILE = "PROFILE"
  AUTH = "AUTH"
  ADMIN = "ADMIN"
  VALIDATION = "VALIDATION"
  SEARCH = "SEARCH"
  DRAFT = "DRAFT"


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
