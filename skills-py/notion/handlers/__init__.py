"""Handler dispatch table — maps tool names to handler functions."""

from __future__ import annotations

from typing import Any

from ..helpers import ToolResult

# Import all handler modules
from . import blocks, comments, databases, pages, search, users

# Build dispatch table from handler modules
DISPATCH: dict[str, Any] = {}

for mod in (pages, databases, blocks, users, comments, search):
  for name in dir(mod):
    if not name.startswith("notion_"):
      continue
    fn = getattr(mod, name)
    if callable(fn):
      DISPATCH[name] = fn


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> ToolResult:
  """Look up and execute a tool handler by name."""
  handler = DISPATCH.get(name)
  if handler is None:
    return ToolResult(content=f"Unknown tool: {name}", is_error=True)
  result: ToolResult = await handler(arguments)
  return result
