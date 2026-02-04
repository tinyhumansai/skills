from __future__ import annotations

import re
from typing import Any

"""Section: Filter to likely tool names (exclude the skill name itself and common fields)"""


# Filter to likely tool names (exclude the skill name itself and common fields)
def _filter_tool_names(tool_names: list[str], info: dict[str, Any], content: str) -> dict[str, Any]:
  """Filter tool names and find hooks."""
  info["tool_names"] = [
    n for n in tool_names if n != info.get("name") and n not in ("on_load", "on_unload", "on_tick")
  ]

  # Find defined hooks
  hooks_found = []
  for hook in (
    "on_load",
    "on_unload",
    "on_session_start",
    "on_session_end",
    "on_before_message",
    "on_after_response",
    "on_tick",
  ):
    if re.search(rf"{hook}\s*=\s*\w", content):
      hooks_found.append(hook)
  info["hooks"] = hooks_found

  return info
