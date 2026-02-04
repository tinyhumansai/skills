"""Handler dispatch table — maps tool names to handler functions."""

from __future__ import annotations

from typing import Any

from ..helpers import ToolResult

# Import all handler modules
from . import actions, api, code, gist, issue, notification, pr, release, repo, search

# Build dispatch table from handler modules
DISPATCH: dict[str, Any] = {}

for mod in (repo, issue, pr, search, code, release, gist, actions, notification, api):
  for name in dir(mod):
    fn = getattr(mod, name)
    if callable(fn) and not name.startswith("_"):
      DISPATCH[name] = fn


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> ToolResult:
  """Look up and execute a tool handler by name."""
  handler = DISPATCH.get(name)
  if handler is None:
    return ToolResult(content=f"Unknown tool: {name}", is_error=True)
  result: ToolResult = await handler(arguments)
  return result
