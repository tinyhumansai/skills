"""
Tool dispatch — routes tool names to handler functions.
"""

from __future__ import annotations

import logging
from typing import Any

from ..tools import ALL_TOOLS

log = logging.getLogger("skill.calendar.handlers")

# Import all handlers
from .calendar import (
  get_calendar,
  list_calendars,
)
from .event import (
  create_event,
  delete_event,
  get_event,
  list_events,
  search_events,
  update_event,
)

# Map tool names to handler functions
HANDLERS: dict[str, Any] = {
  # Calendar tools
  "list_calendars": list_calendars,
  "get_calendar": get_calendar,
  # Event tools
  "list_events": list_events,
  "get_event": get_event,
  "create_event": create_event,
  "update_event": update_event,
  "delete_event": delete_event,
  "search_events": search_events,
}


async def dispatch_tool(tool_name: str, args: dict[str, Any]) -> Any:
  """Dispatch a tool call to the appropriate handler."""
  handler = HANDLERS.get(tool_name)
  if not handler:
    log.error("Unknown tool: %s", tool_name)
    return {"content": f"Unknown tool: {tool_name}", "is_error": True}

  try:
    return await handler(args)
  except Exception as e:
    log.exception("Error executing tool %s: %s", tool_name, e)
    return {"content": f"Error: {e!s}", "is_error": True}
