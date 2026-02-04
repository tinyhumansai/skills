"""
Shared formatting and error handling helpers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger("skill.onepassword.helpers")


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


def format_item_summary(item: dict) -> str:
  """Format a single item as a summary line."""
  title = item.get("title", "Untitled")
  item_id = item.get("id", "unknown")
  vault = item.get("vault", {}).get("name", "unknown")
  category = item.get("category", "unknown")

  return f"{title} ({category}) - Vault: {vault} (ID: {item_id})"


def format_item_detail(item: dict) -> str:
  """Format a full item for display."""
  lines = []

  lines.append(f"Title: {item.get('title', 'Untitled')}")
  lines.append(f"ID: {item.get('id', 'unknown')}")

  if item.get("vault"):
    vault_name = item["vault"].get("name", "unknown")
    lines.append(f"Vault: {vault_name}")

  if item.get("category"):
    lines.append(f"Category: {item['category']}")

  if item.get("tags"):
    tags = ", ".join(item["tags"])
    lines.append(f"Tags: {tags}")

  if item.get("fields"):
    lines.append("\nFields:")
    for field in item["fields"]:
      field_label = field.get("label", "Unknown")
      field_type = field.get("type", "unknown")
      # Don't show password values in detail view
      if field_type == "concealed":
        lines.append(f"  - {field_label}: [password]")
      else:
        value = field.get("value", "")
        lines.append(f"  - {field_label}: {value}")

  if item.get("urls"):
    lines.append("\nURLs:")
    for url_obj in item["urls"]:
      url = url_obj.get("href", "")
      if url:
        lines.append(f"  - {url}")

  return "\n".join(lines)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class ErrorCategory(str, Enum):
  ITEM = "ITEM"
  FIELD = "FIELD"
  AUTH = "AUTH"
  VALIDATION = "VALIDATION"
  CLI = "CLI"


def log_and_format_error(
  function_name: str,
  error: Exception,
  category: str | ErrorCategory | None = None,
) -> ToolResult:
  prefix = category.value if isinstance(category, ErrorCategory) else (category or "GEN")
  hash_val = sum(ord(c) for c in function_name) % 1000
  error_code = f"{prefix}-ERR-{hash_val:03d}"

  log.error("[1Password] Error in %s - Code: %s - %s", function_name, error_code, error)

  from .validation import ValidationError

  if isinstance(error, ValidationError):
    user_message = str(error)
  else:
    user_message = f"An error occurred (code: {error_code}). Check logs for details."

  return ToolResult(content=user_message, is_error=True)
