"""
MCP server + skill lifecycle hooks.

Uses the official `mcp` Python SDK. Handles tools/list, tools/call,
and skill lifecycle methods (load, unload, tick, session events).
Integrates with the SkillServer from dev.runtime.server for reverse RPC.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .tools import ALL_TOOLS
from .handlers import dispatch_tool
from .client.telethon_client import create_client, get_client
from .state import store
from .state.sync import init_host_sync
from .db.connection import init_db, close_db, get_db
from .db.summaries import generate_summaries
from .events.handlers import register_event_handlers

log = logging.getLogger("skill.telegram.server")


def create_mcp_server() -> Server:
    """Create and configure the MCP server with all tool handlers."""
    server = Server("telegram-skill")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return ALL_TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        args = arguments or {}
        result = await dispatch_tool(name, args)
        return [TextContent(type="text", text=result.content)]

    return server


async def on_skill_load(
    params: dict[str, Any],
    set_state_fn: Any = None,
) -> None:
    """Called when the host loads this skill. Initializes Telethon + SQLite."""
    api_id = int(os.environ.get("TELEGRAM_API_ID", params.get("apiId", "0")))
    api_hash = os.environ.get("TELEGRAM_API_HASH", params.get("apiHash", ""))
    session_string = params.get("sessionString", "")
    data_dir = params.get("dataDir", "data")

    if not api_id or not api_hash:
        log.error("Missing TELEGRAM_API_ID or TELEGRAM_API_HASH")
        return

    # Initialize SQLite
    await init_db(data_dir)

    # Initialize Telethon client
    client = create_client(api_id, api_hash)
    await client.initialize(session_string)

    # Connect and check auth
    store.set_connection_status("connecting")
    try:
        await client.connect()
        store.set_connection_status("connected")

        is_authed = await client.check_connection()
        if is_authed:
            store.set_auth_status("authenticated")
            store.set_is_initialized(True)

            # Fetch current user
            me = await client.get_client().get_me()
            if me:
                from .client.builders import build_user
                store.set_current_user(build_user(me))

            # Register event handlers for real-time updates
            await register_event_handlers(client.get_client())
        else:
            store.set_auth_status("not_authenticated")
    except Exception:
        log.exception("Failed to connect/authenticate")
        store.set_connection_status("error")

    # Initialize host sync if available
    if set_state_fn:
        init_host_sync(set_state_fn)

    log.info("Skill loaded successfully")


async def on_skill_unload() -> None:
    """Called when the host unloads this skill."""
    try:
        client = get_client()
        await client.disconnect()
    except Exception:
        log.exception("Error disconnecting client")

    await close_db()
    store.reset_state()
    log.info("Skill unloaded")


async def on_skill_tick() -> None:
    """Called periodically (every 20 minutes). Generates summaries."""
    try:
        db = await get_db()
        await generate_summaries(db, store)
    except Exception:
        log.exception("Error during tick")


async def run_server() -> None:
    """Run the MCP server on stdio."""
    server = create_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
