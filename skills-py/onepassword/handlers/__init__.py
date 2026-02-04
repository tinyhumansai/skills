"""
Tool dispatch — routes tool names to handler functions.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("skill.onepassword.handlers")

# Import all handlers
from .item import (
  get_field_handler,
  get_item_handler,
  get_password_handler,
  list_items_handler,
  search_items_handler,
)

# Map tool names to handler functions
HANDLERS: dict[str, Any] = {
  "list_items": list_items_handler,
  "get_item": get_item_handler,
  "get_password": get_password_handler,
  "get_field": get_field_handler,
  "search_items": search_items_handler,
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
