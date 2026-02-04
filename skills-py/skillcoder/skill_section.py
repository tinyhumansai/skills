from __future__ import annotations

from typing import Any

from dev.types.skill_types import (
  SkillContext,
  SkillDefinition,
  SkillHooks,
  SkillTool,
)

"""Section: ---------------------------------------------------------------------------"""

# ---------------------------------------------------------------------------
# Stub definitions - these are placeholders that will be replaced by the actual
# skill generator. This file is meant to be imported, and if it fails, skill.py
# will fall back to a minimal definition.

TOOL_CATEGORY_OPTIONS: list[Any] = []


async def _on_load(ctx: SkillContext) -> None:
  pass


async def _on_session_start(ctx: SkillContext, session_id: str) -> None:
  pass


async def _on_before_message(ctx: SkillContext, content: str) -> str | None:
  return None


async def _on_unload(ctx: SkillContext) -> None:
  pass


async def _on_status(ctx: SkillContext) -> dict[str, Any]:
  return {}


_TOOLS: list[SkillTool] = []

skill = SkillDefinition(
  name="skill-generator",
  description="Meta-skill that creates, validates, tests, and scans new AlphaHuman skills on-the-fly.",
  version="1.0.0",
  options=TOOL_CATEGORY_OPTIONS,
  hooks=SkillHooks(
    on_load=_on_load,
    on_session_start=_on_session_start,
    on_before_message=_on_before_message,
    on_unload=_on_unload,
    on_status=_on_status,
  ),
  tools=_TOOLS,
)
