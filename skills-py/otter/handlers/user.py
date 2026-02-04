"""
User/speaker domain tool handlers.
"""

from __future__ import annotations

from typing import Any

from ..api import speech_api
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..state import store


async def get_otter_user(args: dict[str, Any]) -> ToolResult:
  try:
    # Check state cache first
    state = store.get_state()
    if state.current_user:
      user = state.current_user
      return ToolResult(
        content=(
          f"Otter.ai User Profile:\n"
          f"  Name: {user.name or 'N/A'}\n"
          f"  Email: {user.email or 'N/A'}\n"
          f"  ID: {user.id or 'N/A'}"
        )
      )

    # Fetch from API
    user = await speech_api.fetch_user()
    if not user:
      return ToolResult(content="Could not retrieve user profile.", is_error=True)

    return ToolResult(
      content=(
        f"Otter.ai User Profile:\n"
        f"  Name: {user.name or 'N/A'}\n"
        f"  Email: {user.email or 'N/A'}\n"
        f"  ID: {user.id or 'N/A'}"
      )
    )
  except Exception as e:
    return log_and_format_error("get_otter_user", e, ErrorCategory.USER)


async def list_speakers(args: dict[str, Any]) -> ToolResult:
  try:
    # Check state cache first
    state = store.get_state()
    if state.speakers:
      speakers = list(state.speakers.values())
    else:
      speakers = await speech_api.fetch_speakers()

    if not speakers:
      return ToolResult(content="No speakers found.")

    lines = []
    for s in speakers:
      lines.append(f"[{s.speaker_id}] {s.name or 'Unknown'}")

    return ToolResult(content=f"Found {len(speakers)} speaker(s):\n" + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_speakers", e, ErrorCategory.USER)
