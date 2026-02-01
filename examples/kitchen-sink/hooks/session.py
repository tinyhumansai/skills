"""
Session lifecycle hooks — session start and end.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json

from dev.types.skill_types import SkillContext


def _now() -> str:
  """Get current timestamp."""
  return datetime.now(timezone.utc).isoformat()


async def on_session_start(ctx: SkillContext, session_id: str) -> None:
  """Called when a new conversation session begins.

  Use this to initialize session-scoped state, greet the user, or
  load session-specific context.

  Demonstrates: session.set, log
  """
  ctx.log(f"kitchen-sink: session started — {session_id}")
  ctx.session.set("message_count", 0)
  ctx.session.set("session_started_at", _now())


async def on_session_end(ctx: SkillContext, session_id: str) -> None:
  """Called when a conversation session ends.

  Use this to persist session summaries, flush analytics, etc.

  Demonstrates: session.get, memory.write, log
  """
  message_count = ctx.session.get("message_count") or 0
  started_at = ctx.session.get("session_started_at") or "unknown"

  ctx.log(
    f"kitchen-sink: session ended — {session_id} ({message_count} messages since {started_at})"
  )

  # Save a session summary to memory for future context
  if message_count > 0:
    await ctx.memory.write(
      f"session-summary/{session_id}",
      json.dumps(
        {
          "session_id": session_id,
          "message_count": message_count,
          "started_at": started_at,
          "ended_at": _now(),
        }
      ),
    )
