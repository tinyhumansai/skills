"""
MCP server + skill lifecycle hooks.

Uses the official `mcp` Python SDK. Handles tools/list, tools/call,
and skill lifecycle methods (load, unload, tick).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client.imap_client import create_imap_client, get_imap_client
from .client.smtp_client import configure_smtp
from .db.connection import close_db, get_db, init_db
from .db.sync import refresh_folder_list, sync_all_watched_folders
from .handlers import dispatch_tool
from .state import store
from .state.sync import init_host_sync
from .state.types import EmailAccount
from .tools import ALL_TOOLS

log = logging.getLogger("skill.email.server")


def create_mcp_server() -> Server:
  """Create and configure the MCP server with all tool handlers."""
  server = Server("email-skill")

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
  """Called when the host loads this skill. Initializes IMAP + SMTP + SQLite."""
  data_dir = params.get("dataDir", "data")

  # Read config
  config: dict[str, Any] = params.get("config", {})

  if not config:
    log.warning("No config found — skill needs setup")
    return

  email_addr = config.get("email", "")
  password = config.get("password", "")
  imap_host = config.get("imap_host", "")
  imap_port = int(config.get("imap_port", 993))
  smtp_host = config.get("smtp_host", "")
  smtp_port = int(config.get("smtp_port", 587))
  use_ssl = bool(config.get("use_ssl", True))
  provider = config.get("provider", "custom")

  if not email_addr or not password or not imap_host:
    log.error("Missing required config: email, password, or imap_host")
    return

  # Initialize SQLite
  await init_db(data_dir)

  # Set account info in store
  account = EmailAccount(
    email=email_addr,
    provider=provider,
    imap_host=imap_host,
    imap_port=imap_port,
    smtp_host=smtp_host,
    smtp_port=smtp_port,
    use_ssl=use_ssl,
  )
  store.set_account(account)

  # Set account ID on API modules
  from .api import attachment_api, draft_api, flag_api, message_api

  message_api.set_account_id(email_addr)
  flag_api.set_account_id(email_addr)
  attachment_api.set_account_id(email_addr)
  attachment_api.set_data_dir(data_dir)
  draft_api.set_account_id(email_addr)

  # Initialize IMAP client
  imap_client = create_imap_client(imap_host, imap_port, use_ssl)
  store.set_connection_status("connecting")

  try:
    connected = await imap_client.connect(email_addr, password)
    if connected:
      store.set_connection_status("connected")
      store.set_is_initialized(True)

      # Refresh folder list
      db = await get_db()
      await refresh_folder_list(db, email_addr)

      # Initial sync of INBOX
      await sync_all_watched_folders(db, email_addr)
      store.set_last_sync(time.time())
    else:
      store.set_connection_status("error")
      store.set_connection_error("IMAP connection failed")
  except Exception:
    log.exception("Failed to connect IMAP")
    store.set_connection_status("error")

  # Configure SMTP
  configure_smtp(smtp_host, smtp_port, email_addr, password, use_ssl)

  # Initialize host sync if available
  if set_state_fn:
    init_host_sync(set_state_fn)

  log.info("Email skill loaded successfully")


async def on_skill_unload() -> None:
  """Called when the host unloads this skill."""
  try:
    client = get_imap_client()
    if client:
      await client.disconnect()
  except Exception:
    log.exception("Error disconnecting IMAP client")

  await close_db()
  store.reset_state()
  log.info("Email skill unloaded")


async def on_skill_tick() -> None:
  """Called every 5 minutes. Syncs INBOX and refreshes folder status."""
  state = store.get_state()
  if not state.is_initialized or not state.account:
    return

  account_id = state.account.email

  # NOOP keepalive
  client = get_imap_client()
  if client and not await client.noop():
    # Try to reconnect
    log.warning("IMAP keepalive failed, reconnecting...")
    store.set_connection_status("connecting")
    if await client.ensure_connected():
      store.set_connection_status("connected")
    else:
      store.set_connection_status("error")
      return

  # Incremental sync
  store.set_sync_status(True)
  try:
    db = await get_db()
    results = await sync_all_watched_folders(db, account_id)
    total_new = sum(results.values())
    if total_new > 0:
      log.info("Synced %d new messages", total_new)

    # Refresh folder list periodically
    await refresh_folder_list(db, account_id)

    store.set_last_sync(time.time())
  except Exception:
    log.exception("Error during tick sync")
  finally:
    store.set_sync_status(False)


async def run_server() -> None:
  """Run the MCP server on stdio."""
  server = create_mcp_server()
  async with stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, server.create_initialization_options())
