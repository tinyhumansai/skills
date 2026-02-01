"""
Tick hook — periodic background tasks.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from dev.types.skill_types import SkillContext


def _now() -> str:
  """Get current timestamp."""
  return datetime.now(timezone.utc).isoformat()


async def on_tick(ctx: SkillContext) -> None:
  """Called periodically at the configured tick_interval (60 seconds).

  Use this for background tasks: polling APIs, syncing data,
  generating summaries, cleaning up stale data.

  Demonstrates: get_state, set_state, memory.list, log, emit_event
  """
  state = ctx.get_state() or {}
  tick_count = state.get("tick_count", 0) + 1
  ctx.set_state({"tick_count": tick_count, "last_tick": _now()})

  ctx.log(f"kitchen-sink: tick #{tick_count}")

  # Persist the notes index to memory so it survives compaction
  notes_index = state.get("notes_index", [])
  if notes_index:
    await ctx.memory.write(
      "kitchen-sink/notes-index",
      json.dumps(notes_index),
    )

  # Example: every 10 ticks (10 minutes), emit a summary event
  if tick_count % 10 == 0:
    ctx.emit_event("periodic_summary", {"tick_count": tick_count, "timestamp": _now()})
