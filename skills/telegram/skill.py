"""
Telegram SkillDefinition — wires setup, tools, and lifecycle hooks
into the unified SkillServer protocol.

Usage:
    from skills.telegram.skill import skill
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from dev.types.skill_types import (
    SkillDefinition,
    SkillHooks,
    SkillTool,
    ToolDefinition,
    ToolResult as SkillToolResult,
)
from dev.types.setup_types import SetupStep, SetupResult

from .setup import on_setup_start, on_setup_submit, on_setup_cancel
from .tools import ALL_TOOLS
from .handlers import dispatch_tool

log = logging.getLogger("skill.telegram.skill")


# ---------------------------------------------------------------------------
# Convert MCP Tool objects → SkillTool objects
# ---------------------------------------------------------------------------


def _make_execute(tool_name: str):
    """Create an async execute function for a given tool name."""

    async def execute(args: dict[str, Any]) -> SkillToolResult:
        result = await dispatch_tool(tool_name, args)
        return SkillToolResult(content=result.content, is_error=result.is_error)

    return execute


def _convert_tools() -> list[SkillTool]:
    """Convert MCP Tool definitions to SkillTool objects."""
    skill_tools: list[SkillTool] = []
    for mcp_tool in ALL_TOOLS:
        schema = mcp_tool.inputSchema if isinstance(mcp_tool.inputSchema, dict) else {}
        definition = ToolDefinition(
            name=mcp_tool.name,
            description=mcp_tool.description or "",
            parameters=schema,
        )
        skill_tools.append(
            SkillTool(
                definition=definition,
                execute=_make_execute(mcp_tool.name),
            )
        )
    return skill_tools


# ---------------------------------------------------------------------------
# Lifecycle hooks adapted for SkillContext
# ---------------------------------------------------------------------------


async def _on_load(ctx: Any) -> None:
    """Initialize Telethon + SQLite using SkillContext."""
    from .server import on_skill_load

    # Read config from data dir if it exists
    config: dict[str, Any] = {}
    try:
        raw = await ctx.read_data("config.json")
        if raw:
            config = json.loads(raw)
            log.info("Loaded config.json: keys=%s, has_session=%s", list(config.keys()), bool(config.get("session_string")))
        else:
            log.info("config.json is empty or not found")
    except Exception as exc:
        log.warning("Failed to read config.json: %s", exc)

    # Build params dict that on_skill_load expects
    params: dict[str, Any] = {
        "dataDir": ctx.data_dir,
        "sessionString": config.get("session_string", ""),
        "apiId": config.get("api_id", os.environ.get("TELEGRAM_API_ID", "")),
        "apiHash": config.get("api_hash", os.environ.get("TELEGRAM_API_HASH", "")),
    }

    # Pass set_state as an async callback for host sync.
    # sync.py awaits this callback, so it must be a coroutine.
    async def set_state_fn(partial: dict[str, Any]) -> None:
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
    from .state.store import get_state
    state = get_state()
    return {
        "connection_status": state.connection_status,
        "auth_status": state.auth_status,
        "is_initialized": state.is_initialized,
        "connection_error": state.connection_error,
        "auth_error": state.auth_error,
        "current_user": state.current_user.model_dump() if state.current_user else None,
    }


# ---------------------------------------------------------------------------
# Skill definition
# ---------------------------------------------------------------------------

skill = SkillDefinition(
    name="telegram",
    description="Telegram integration via Telethon MTProto — 75+ tools for chats, messages, contacts, admin, media, and settings.",
    version="2.0.0",
    has_setup=True,
    tick_interval=1_200_000,  # 20 minutes
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
