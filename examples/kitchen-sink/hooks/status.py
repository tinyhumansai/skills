"""
Status hook — return current skill status information.
"""

from __future__ import annotations

from typing import Any

from dev.types.skill_types import SkillContext


async def on_status(ctx: SkillContext) -> dict[str, Any]:
  """Return current skill status information.

  Demonstrates: get_state, status reporting
  """
  state = ctx.get_state() or {}
  config = state.get("config")

  return {
    "configured": config is not None,
    "username": config.get("username") if config else None,
    "notes_count": len(state.get("notes_index", [])),
    "tick_count": state.get("tick_count", 0),
  }
