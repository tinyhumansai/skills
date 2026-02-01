"""
Event management tool handlers.
"""

from __future__ import annotations

from typing import Any

from ..api import event_api
from ..helpers import (
  ErrorCategory,
  ToolResult,
  format_event_detail,
  format_event_summary,
  log_and_format_error,
)
from ..validation import opt_bool, opt_number, opt_string, require_string


async def list_events(args: dict[str, Any]) -> ToolResult:
  try:
    calendar_id = opt_string(args, "calendar_id") or "primary"
    time_min = opt_string(args, "time_min")
    time_max = opt_string(args, "time_max")
    max_results = opt_number(args, "max_results", 50) or 50
    single_events = opt_bool(args, "single_events", True) or True
    order_by = opt_string(args, "order_by") or "startTime"
    
    events = await event_api.list_events(
      calendar_id=calendar_id,
      time_min=time_min,
      time_max=time_max,
      max_results=max_results,
      single_events=single_events,
      order_by=order_by,
    )
    
    if not events:
      return ToolResult(content=f"No events found in calendar '{calendar_id}'.")
    
    lines = [format_event_summary(event) for event in events]
    header = f"Events in '{calendar_id}' ({len(events)} shown):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_events", e, ErrorCategory.EVENT)


async def get_event(args: dict[str, Any]) -> ToolResult:
  try:
    calendar_id = opt_string(args, "calendar_id") or "primary"
    event_id = require_string(args, "event_id")
    
    event = await event_api.get_event(calendar_id, event_id)
    return ToolResult(content=format_event_detail(event))
  except ValueError as e:
    return ToolResult(content=str(e), is_error=True)
  except Exception as e:
    return log_and_format_error("get_event", e, ErrorCategory.EVENT)


async def create_event(args: dict[str, Any]) -> ToolResult:
  try:
    calendar_id = opt_string(args, "calendar_id") or "primary"
    title = require_string(args, "title")
    start = require_string(args, "start")
    end = require_string(args, "end")
    description = opt_string(args, "description")
    location = opt_string(args, "location")
    all_day = opt_bool(args, "all_day", False) or False
    attendees = args.get("attendees")
    if attendees and isinstance(attendees, list):
      attendees = [str(a) for a in attendees if isinstance(a, str)]
    else:
      attendees = None
    timezone = opt_string(args, "timezone")
    
    event = await event_api.create_event(
      calendar_id=calendar_id,
      title=title,
      start=start,
      end=end,
      description=description,
      location=location,
      all_day=all_day,
      attendees=attendees,
      timezone=timezone,
    )
    
    return ToolResult(
      content=f"Event created successfully!\n\n{format_event_detail(event)}"
    )
  except Exception as e:
    return log_and_format_error("create_event", e, ErrorCategory.EVENT)


async def update_event(args: dict[str, Any]) -> ToolResult:
  try:
    calendar_id = opt_string(args, "calendar_id") or "primary"
    event_id = require_string(args, "event_id")
    title = opt_string(args, "title")
    start = opt_string(args, "start")
    end = opt_string(args, "end")
    description = opt_string(args, "description")
    location = opt_string(args, "location")
    all_day = opt_bool(args, "all_day")
    attendees = args.get("attendees")
    if attendees and isinstance(attendees, list):
      attendees = [str(a) for a in attendees if isinstance(a, str)]
    else:
      attendees = None
    
    event = await event_api.update_event(
      calendar_id=calendar_id,
      event_id=event_id,
      title=title,
      start=start,
      end=end,
      description=description,
      location=location,
      all_day=all_day,
      attendees=attendees,
    )
    
    return ToolResult(
      content=f"Event updated successfully!\n\n{format_event_detail(event)}"
    )
  except ValueError as e:
    return ToolResult(content=str(e), is_error=True)
  except Exception as e:
    return log_and_format_error("update_event", e, ErrorCategory.EVENT)


async def delete_event(args: dict[str, Any]) -> ToolResult:
  try:
    calendar_id = opt_string(args, "calendar_id") or "primary"
    event_id = require_string(args, "event_id")
    
    await event_api.delete_event(calendar_id, event_id)
    return ToolResult(content=f"Event {event_id} deleted successfully.")
  except ValueError as e:
    return ToolResult(content=str(e), is_error=True)
  except Exception as e:
    return log_and_format_error("delete_event", e, ErrorCategory.EVENT)


async def search_events(args: dict[str, Any]) -> ToolResult:
  try:
    calendar_id = opt_string(args, "calendar_id") or "primary"
    query = require_string(args, "query")
    time_min = opt_string(args, "time_min")
    time_max = opt_string(args, "time_max")
    max_results = opt_number(args, "max_results", 50) or 50
    
    events = await event_api.search_events(
      calendar_id=calendar_id,
      query=query,
      time_min=time_min,
      time_max=time_max,
      max_results=max_results,
    )
    
    if not events:
      return ToolResult(content=f"No events found matching '{query}'.")
    
    lines = [format_event_summary(event) for event in events]
    header = f"Search results for '{query}' ({len(events)} found):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_events", e, ErrorCategory.EVENT)
