"""
Account info and status tool handlers.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

from ..api import folder_api, message_api
from ..client.imap_client import get_imap_client
from ..client.smtp_client import is_configured as smtp_is_configured
from ..db.connection import get_db
from ..db.queries import search_contacts as db_search_contacts
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..state import store
from ..validation import opt_number, opt_string_list, req_string


async def get_account_info(args: dict[str, Any]) -> ToolResult:
  try:
    state = store.get_state()
    if not state.account:
      return ToolResult(content="No email account connected.", is_error=True)

    account = state.account
    lines = [
      f"Email: {account.email}",
      f"Provider: {account.provider}",
      f"IMAP: {account.imap_host}:{account.imap_port}",
      f"SMTP: {account.smtp_host}:{account.smtp_port}",
      f"SSL: {'Yes' if account.use_ssl else 'No'}",
      f"Connection: {state.connection_status}",
      f"Total unread: {state.total_unread}",
    ]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_account_info", e, ErrorCategory.ACCOUNT)


async def get_mailbox_summary(args: dict[str, Any]) -> ToolResult:
  try:
    folders = await folder_api.list_folders()
    if not folders:
      return ToolResult(content="No folders found.")

    lines = ["Mailbox Summary:"]
    total_messages = 0
    total_unseen = 0

    for f in folders:
      name = f["name"]
      try:
        status = await folder_api.get_folder_status(name)
        exists = status.get("exists", 0)
        unseen = status.get("unseen", 0)
        total_messages += exists
        total_unseen += unseen
        unseen_str = f" ({unseen} unread)" if unseen else ""
        lines.append(f"  {name}: {exists} messages{unseen_str}")
      except Exception:
        lines.append(f"  {name}: (status unavailable)")

    lines.append(f"\nTotal: {total_messages} messages, {total_unseen} unread")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_mailbox_summary", e, ErrorCategory.ACCOUNT)


async def get_unread_count(args: dict[str, Any]) -> ToolResult:
  try:
    folders = opt_string_list(args, "folders")

    if folders:
      lines = []
      total = 0
      for folder in folders:
        count = await message_api.get_unread_count(folder)
        total += count
        lines.append(f"{folder}: {count} unread")
      lines.append(f"Total: {total} unread")
      return ToolResult(content="\n".join(lines))
    else:
      count = await message_api.get_unread_count()
      return ToolResult(content=f"Total unread: {count}")
  except Exception as e:
    return log_and_format_error("get_unread_count", e, ErrorCategory.ACCOUNT)


async def test_connection(args: dict[str, Any]) -> ToolResult:
  try:
    lines = []

    # Test IMAP
    client = get_imap_client()
    if client:
      imap_ok = await client.ensure_connected()
      lines.append(f"IMAP: {'Connected' if imap_ok else 'Disconnected'}")
    else:
      lines.append("IMAP: Not configured")

    # Test SMTP
    if smtp_is_configured():
      lines.append("SMTP: Configured")
    else:
      lines.append("SMTP: Not configured")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("test_connection", e, ErrorCategory.ACCOUNT)


async def get_sync_status(args: dict[str, Any]) -> ToolResult:
  try:
    state = store.get_state()
    lines = [
      f"Connection: {state.connection_status}",
      f"Initialized: {state.is_initialized}",
      f"Syncing: {state.is_syncing}",
    ]
    if state.last_sync:
      from datetime import datetime

      last = datetime.fromtimestamp(state.last_sync, tz=UTC).isoformat()
      lines.append(f"Last sync: {last}")
    else:
      lines.append("Last sync: Never")

    lines.append(f"Folders: {len(state.folders)}")
    lines.append(f"Total unread: {state.total_unread}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_sync_status", e, ErrorCategory.SYNC)


async def search_contacts(args: dict[str, Any]) -> ToolResult:
  try:
    query = req_string(args, "query")
    limit = opt_number(args, "limit", 20)

    db = await get_db()
    contacts = await db_search_contacts(db, query, limit)
    if not contacts:
      return ToolResult(content="No contacts match the search.")

    lines = []
    for c in contacts:
      name = f"{c.display_name} " if c.display_name else ""
      lines.append(f"{name}<{c.email}> ({c.message_count} messages)")

    header = f"Contacts matching '{query}' ({len(contacts)}):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_contacts", e, ErrorCategory.SEARCH)
