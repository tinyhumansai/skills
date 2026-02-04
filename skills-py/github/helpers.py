"""
Shared formatting and error handling helpers for the GitHub skill.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

log = logging.getLogger("skill.github.helpers")


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
  REPO = "REPO"
  ISSUE = "ISSUE"
  PR = "PR"
  RELEASE = "RELEASE"
  GIST = "GIST"
  ACTIONS = "ACTIONS"
  SEARCH = "SEARCH"
  CODE = "CODE"
  NOTIFY = "NOTIFY"
  AUTH = "AUTH"
  VALIDATION = "VALIDATION"
  API = "API"


def log_and_format_error(
  function_name: str,
  error: Exception,
  category: str | ErrorCategory | None = None,
) -> ToolResult:
  prefix = category.value if isinstance(category, ErrorCategory) else (category or "GEN")
  hash_val = sum(ord(c) for c in function_name) % 1000
  error_code = f"{prefix}-ERR-{hash_val:03d}"

  log.error("[GH] Error in %s - Code: %s - %s", function_name, error_code, error)

  from .validation import ValidationError

  if isinstance(error, ValidationError):
    user_message = str(error)
  else:
    user_message = f"An error occurred (code: {error_code}). Check logs for details."

  return ToolResult(content=user_message, is_error=True)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_repo_line(r: dict[str, Any]) -> str:
  """Format a single repo dict into a display line."""
  name = r.get("nameWithOwner") or r.get("fullName") or r.get("name", "?")
  desc = r.get("description") or ""
  stars = r.get("stargazerCount", r.get("stargazers_count", ""))
  vis = r.get("visibility", r.get("private", ""))
  if isinstance(vis, bool):
    vis = "private" if vis else "public"
  parts = [name]
  if vis:
    parts.append(f"[{vis}]")
  if stars != "":
    parts.append(f"({stars} stars)")
  if desc:
    parts.append(f"- {desc[:80]}")
  return " ".join(parts)


def format_issue_line(i: dict[str, Any]) -> str:
  """Format a single issue/PR dict into a display line."""
  number = i.get("number", "?")
  title = i.get("title", "")
  state = i.get("state", "")
  author = ""
  if isinstance(i.get("author"), dict):
    author = i["author"].get("login", "")
  elif isinstance(i.get("user"), dict):
    author = i["user"].get("login", "")
  labels = ""
  raw_labels = i.get("labels", [])
  if raw_labels:
    if isinstance(raw_labels[0], dict):
      labels = ", ".join(l.get("name", "") for l in raw_labels[:3])
    elif isinstance(raw_labels[0], str):
      labels = ", ".join(raw_labels[:3])
  parts = [f"#{number}", f"[{state}]" if state else "", title[:80]]
  if author:
    parts.append(f"(by @{author})")
  if labels:
    parts.append(f"[{labels}]")
  return " ".join(p for p in parts if p)


def truncate(text: str, max_len: int = 4000) -> str:
  """Truncate text to max_len with ellipsis indicator."""
  if len(text) <= max_len:
    return text
  return text[: max_len - 20] + "\n... (truncated)"
