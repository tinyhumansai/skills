"""
Shared formatting and error handling helpers for the Otter.ai skill.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Literal

log = logging.getLogger("skill.otter.helpers")


# ---------------------------------------------------------------------------
# Tool result
# ---------------------------------------------------------------------------


@dataclass
class ToolResult:
  content: str
  is_error: bool = False


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class ErrorCategory(str, Enum):
  SPEECH = "SPEECH"
  SEARCH = "SEARCH"
  USER = "USER"
  TRANSCRIPT = "TRANSCRIPT"
  AUTH = "AUTH"
  VALIDATION = "VALIDATION"


def log_and_format_error(
  function_name: str,
  error: Exception,
  category: str | ErrorCategory | None = None,
) -> ToolResult:
  prefix = category.value if isinstance(category, ErrorCategory) else (category or "GEN")
  hash_val = sum(ord(c) for c in function_name) % 1000
  error_code = f"{prefix}-ERR-{hash_val:03d}"

  log.error("[Otter] Error in %s - Code: %s - %s", function_name, error_code, error)

  from .validation import ValidationError

  if isinstance(error, ValidationError):
    user_message = str(error)
  else:
    user_message = f"An error occurred (code: {error_code}). Check logs for details."

  return ToolResult(content=user_message, is_error=True)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

MAX_TRANSCRIPT_CHARS = 8000


def truncate_transcript(text: str, max_chars: int = MAX_TRANSCRIPT_CHARS) -> str:
  """Truncate transcript text to fit within tool response limits."""
  if len(text) <= max_chars:
    return text
  return text[:max_chars] + f"\n\n[Transcript truncated — {len(text)} total characters]"


def format_duration(seconds: float) -> str:
  """Format duration in seconds to human-readable string."""
  if seconds < 60:
    return f"{int(seconds)}s"
  minutes = int(seconds // 60)
  secs = int(seconds % 60)
  if minutes < 60:
    return f"{minutes}m {secs}s"
  hours = minutes // 60
  mins = minutes % 60
  return f"{hours}h {mins}m"


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

ToolTier = Literal["state_only", "api_read"]

_RATE_LIMIT = {
  "API_READ_DELAY_MS": 500,
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

  required_delay = _RATE_LIMIT["API_READ_DELAY_MS"]

  now_ms = time.time() * 1000
  elapsed = now_ms - _last_call_time
  if elapsed < required_delay:
    await asyncio.sleep((required_delay - elapsed) / 1000)

  _last_call_time = time.time() * 1000
  _call_history.append(_last_call_time)
