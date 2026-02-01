"""
Session information tools.
"""

from __future__ import annotations

from dev.types.skill_types import SkillContext, ToolResult


async def execute_get_session_info(args: dict) -> ToolResult:
  """Return current session information.

  Demonstrates: session.id, session.get
  """
  ctx: SkillContext = args.pop("__context__")

  session_id = ctx.session.id
  message_count = ctx.session.get("message_count") or 0

  return ToolResult(content=f"Session ID: {session_id}\nMessages in session: {message_count}")
