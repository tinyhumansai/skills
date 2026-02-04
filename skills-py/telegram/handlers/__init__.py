"""Handler dispatch table — maps tool names to handler functions."""

from __future__ import annotations

from typing import Any

from ..helpers import ToolResult

# Import all handler modules
from . import admin, chat, contact, media, message, search, settings

# Build dispatch table from handler modules
DISPATCH: dict[str, Any] = {}

for mod in (chat, message, contact, admin, media, settings, search):
  for name in dir(mod):
    fn = getattr(mod, name)
    if callable(fn) and not name.startswith("_"):
      DISPATCH[name] = fn


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> ToolResult:
  """Look up and execute a tool handler by name."""
  # Convert tool name from hyphenated (e.g., "get-chats") to underscore format (e.g., "get_chats")
  # for Python function name lookup
  handler_name = name.replace("-", "_")
  handler = DISPATCH.get(handler_name)
  if handler is None:
    return ToolResult(content=f"Unknown tool: {name}", is_error=True)
  return await handler(arguments)
