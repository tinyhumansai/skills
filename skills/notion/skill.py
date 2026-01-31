"""
Notion SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.

Usage:
    from skills.notion.skill import skill
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dev.types.skill_types import (
    SkillDefinition,
    SkillHooks,
    SkillTool,
    ToolResult as SkillToolResult,
)
from dev.types.setup_types import SetupStep, SetupResult

from .setup import on_setup_start, on_setup_submit, on_setup_cancel
from .tools import ALL_TOOLS
from .handlers import dispatch_tool

log = logging.getLogger("skill.notion.skill")


# ---------------------------------------------------------------------------
# Convert ToolDefinition objects → SkillTool objects
# ---------------------------------------------------------------------------


def _make_execute(tool_name: str):
    """Create an async execute function for a given tool name."""

    async def execute(args: dict[str, Any]) -> SkillToolResult:
        result = await dispatch_tool(tool_name, args)
        return SkillToolResult(content=result.content, is_error=result.is_error)

    return execute


def _convert_tools() -> list[SkillTool]:
    """Convert ToolDefinition objects to SkillTool objects with execute functions."""
    skill_tools: list[SkillTool] = []
    for tool_def in ALL_TOOLS:
        skill_tools.append(
            SkillTool(
                definition=tool_def,
                execute=_make_execute(tool_def.name),
            )
        )
    return skill_tools


# ---------------------------------------------------------------------------
# Lifecycle hooks adapted for SkillContext
# ---------------------------------------------------------------------------


async def _on_load(ctx: Any) -> None:
    """Initialize Notion client using SkillContext."""
    from .server import on_skill_load

    # Read config from data dir if it exists
    config: dict[str, Any] = {}
    try:
        raw = await ctx.read_data("config.json")
        if raw:
            config = json.loads(raw)
    except Exception:
        pass

    # Build params dict that on_skill_load expects
    params: dict[str, Any] = {
        "token": config.get("token", ""),
    }

    # Pass set_state as a callback for host sync
    def set_state_fn(partial: dict[str, Any]) -> None:
        ctx.set_state(partial)

    await on_skill_load(params, set_state_fn=set_state_fn)


async def _on_unload(ctx: Any) -> None:
    from .server import on_skill_unload
    await on_skill_unload()


async def _on_tick(ctx: Any) -> None:
    from .server import on_skill_tick
    await on_skill_tick()


async def _on_status(ctx: Any) -> dict[str, Any]:
    """Return current skill status information."""
    from .client import get_client
    try:
        client = get_client()
        if client:
            # Try to get user info to verify connection
            me = await client.users.me()
            return {
                "connected": True,
                "bot_name": me.get("name", "integration"),
                "bot_id": me.get("id", ""),
            }
        return {
            "connected": False,
            "bot_name": None,
            "bot_id": None,
        }
    except Exception:
        return {
            "connected": False,
            "bot_name": None,
            "bot_id": None,
        }


# ---------------------------------------------------------------------------
# Skill definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
    name="notion",
    description="Notion workspace integration — 22 tools for pages, databases, blocks, users, comments, and search.",
    version="1.0.0",
    has_setup=True,
    tick_interval=300_000,  # 5 minutes
    tools=_convert_tools(),
    hooks=SkillHooks(
        on_load=_on_load,
        on_unload=_on_unload,
        on_tick=_on_tick,
        on_status=_on_status,
        on_setup_start=on_setup_start,
        on_setup_submit=on_setup_submit,
        on_setup_cancel=on_setup_cancel,
    ),
)
