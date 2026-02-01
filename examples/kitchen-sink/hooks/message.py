"""
Message hooks — transform messages before/after AI processing.
"""

from __future__ import annotations

from dev.types.skill_types import SkillContext


async def on_before_message(ctx: SkillContext, message: str) -> str | None:
  """Called before each user message is sent to the AI.

  Return a string to transform/augment the message.
  Return None to pass it through unchanged.

  Demonstrates: session.get/set, get_state, message transformation
  """
  # Track message count in session
  count = (ctx.session.get("message_count") or 0) + 1
  ctx.session.set("message_count", count)

  # Example: inject context from config into the first message
  state = ctx.get_state() or {}
  config = state.get("config")
  if count == 1 and config:
    username = config.get("username", "User")
    preferences = config.get("preferences", [])
    prefs_str = ", ".join(preferences) if preferences else "none set"
    context_block = f"\n\n[System context from kitchen-sink skill: User is '{username}', preferences: {prefs_str}]"
    return message + context_block

  return None  # No transformation


async def on_after_response(ctx: SkillContext, response: str) -> str | None:
  """Called after the AI generates a response, before it's shown to the user.

  Return a string to transform the response.
  Return None to pass it through unchanged.

  Demonstrates: response transformation
  """
  # Example: append a subtle footer on every 5th message
  count = ctx.session.get("message_count") or 0
  if count > 0 and count % 5 == 0:
    footer = "\n\n_[Powered by kitchen-sink skill example]_"
    return response + footer

  return None  # No transformation
