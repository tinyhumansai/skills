"""
Calendar management tool handlers.
"""

from __future__ import annotations

from typing import Any

from ..api import calendar_api
from ..helpers import ErrorCategory, ToolResult, format_calendar, log_and_format_error
from ..validation import opt_bool, require_string


async def list_calendars(args: dict[str, Any]) -> ToolResult:
  try:
    show_hidden = opt_bool(args, "show_hidden", False) or False

    calendars = await calendar_api.list_calendars(show_hidden=show_hidden)
    if not calendars:
      return ToolResult(content="No calendars found.")

    lines = [format_calendar(cal) for cal in calendars]
    header = f"Calendars ({len(calendars)}):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_calendars", e, ErrorCategory.CALENDAR)


async def get_calendar(args: dict[str, Any]) -> ToolResult:
  try:
    calendar_id = require_string(args, "calendar_id")

    calendar = await calendar_api.get_calendar(calendar_id)

    lines = []
    lines.append(f"Calendar ID: {calendar.get('id', 'unknown')}")
    lines.append(f"Name: {calendar.get('summary', 'No name')}")
    if calendar.get("timeZone"):
      lines.append(f"Timezone: {calendar['timeZone']}")
    if calendar.get("description"):
      lines.append(f"Description: {calendar['description']}")
    if calendar.get("primary"):
      lines.append("Primary: Yes")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_calendar", e, ErrorCategory.CALENDAR)
