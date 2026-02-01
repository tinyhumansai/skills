"""
Shared formatting and error handling helpers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger("skill.ccxt.helpers")


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
  ACCOUNT = "ACCOUNT"
  MARKET = "MARKET"
  TRADING = "TRADING"
  VALIDATION = "VALIDATION"
  CONNECTION = "CONNECTION"


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
