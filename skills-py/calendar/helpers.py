"""
Shared formatting and error handling helpers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .validation import ValidationError

log = logging.getLogger("skill.calendar.helpers")


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


def format_event_summary(event: dict) -> str:
  """Format a single event as a summary line."""
  title = event.get("summary", "No title")
  start = event.get("start", {})
  start_time = ""

  if "dateTime" in start:
    try:
      dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
      start_time = dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
      start_time = start.get("dateTime", "")
  elif "date" in start:
    start_time = start["date"]

  event_id = event.get("id", "unknown")
  location = event.get("location", "")
  location_str = f" @ {location}" if location else ""

  return f"{start_time} | {title}{location_str} (ID: {event_id})"


def format_event_detail(event: dict) -> str:
  """Format a full event for display."""
  lines = []

  lines.append(f"Event ID: {event.get('id', 'unknown')}")
  lines.append(f"Title: {event.get('summary', 'No title')}")

  start = event.get("start", {})
  end = event.get("end", {})

  if "dateTime" in start:
    start_time = start["dateTime"]
    end_time = end.get("dateTime", "")
    lines.append(f"Start: {start_time}")
    if end_time:
      lines.append(f"End: {end_time}")
  elif "date" in start:
    lines.append("All-day event")
    lines.append(f"Date: {start['date']}")
    if end.get("date"):
      lines.append(f"End date: {end['date']}")

  if event.get("location"):
    lines.append(f"Location: {event['location']}")

  if event.get("description"):
    lines.append(f"\nDescription:\n{event['description']}")

  attendees = event.get("attendees", [])
  if attendees:
    attendee_emails = [a.get("email", "") for a in attendees if a.get("email")]
    if attendee_emails:
      lines.append(f"\nAttendees: {', '.join(attendee_emails)}")

  status = event.get("status", "")
  if status:
    lines.append(f"Status: {status}")

  return "\n".join(lines)


def format_calendar(calendar: dict) -> str:
  """Format calendar info."""
  name = calendar.get("summary", calendar.get("id", "Unknown"))
  timezone = calendar.get("timeZone", "")
  tz_str = f" ({timezone})" if timezone else ""
  primary = " [PRIMARY]" if calendar.get("primary", False) else ""
  return f"{name}{tz_str}{primary}"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class ErrorCategory(str, Enum):
  CALENDAR = "CALENDAR"
  EVENT = "EVENT"
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

  log.error("[MCP] Error in %s - Code: %s - %s", function_name, error_code, error)

  if isinstance(error, ValidationError):
    user_message = str(error)
  else:
    user_message = f"An error occurred (code: {error_code}). Check logs for details."

  return ToolResult(content=user_message, is_error=True)
