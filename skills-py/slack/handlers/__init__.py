"""Handler dispatch table — maps tool names to handler functions."""

from __future__ import annotations

import inspect
from typing import Any

from ..helpers import ToolResult

# Import all handler modules
from . import channel, message, search, user, workspace

# Build dispatch table from handler modules (async functions only)
DISPATCH: dict[str, Any] = {}

for mod in (channel, message, user, search, workspace):
  for name in dir(mod):
    if name.startswith("_"):
      continue
    fn = getattr(mod, name)
    if inspect.iscoroutinefunction(fn) and fn.__module__ == mod.__name__:
      DISPATCH[name] = fn


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> ToolResult:
  """Look up and execute a tool handler by name."""
  handler = DISPATCH.get(name)
  if handler is None:
    return ToolResult(content=f"Unknown tool: {name}", is_error=True)
  return await handler(arguments)
