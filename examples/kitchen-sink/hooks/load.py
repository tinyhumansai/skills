"""
Load hook — initialize skill on startup.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from dev.types.skill_types import SkillContext


def _now() -> str:
  """Get current timestamp."""
  return datetime.now(timezone.utc).isoformat()


async def _load_configuration(ctx: SkillContext) -> None:
  """Load configuration from setup flow."""
  try:
    raw = await ctx.read_data("config.json")
    config = json.loads(raw)
    ctx.set_state({"config": config, "loaded_at": _now()})
    ctx.log(f"kitchen-sink: loaded config for user '{config.get('username')}'")
  except Exception:
    ctx.set_state({"config": None, "loaded_at": _now()})
    ctx.log("kitchen-sink: no config found (setup not completed)")

  # Initialize notes index if not present
  state = ctx.get_state() or {}
  if "notes_index" not in state:
    ctx.set_state({"notes_index": []})


async def on_load(ctx: SkillContext) -> None:
  """Called once when the skill is loaded at app startup.

  Use this to initialize connections, load configuration,
  restore state, or register initial tools.

  Demonstrates: read_data, write_data, get_state, set_state, log
  """
  await _load_configuration(ctx)

  # Register dynamic tools based on configuration
  from tools.dynamic import _register_dynamic_tools

  await _register_dynamic_tools(ctx)

  ctx.log("kitchen-sink: on_load — initialized")
