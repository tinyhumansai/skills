"""
Search domain tool handlers.

Ported from handlers/search.ts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ..api import search_api
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import opt_number, opt_string


async def search_public_chats(args: dict[str, Any]) -> ToolResult:
  try:
    query = args.get("query", "")
    if not isinstance(query, str) or not query:
      return ToolResult(content="Search query is required", is_error=True)
    limit = opt_number(args, "limit", 20)

    result = await search_api.search_public_chats(query, limit)
    if not result.data:
      return ToolResult(content=f'No public chats found for "{query}".')

    lines = []
    for c in result.data:
      entry_type = c.get("type", "unknown")
      name = c.get("title") or c.get("firstName") or "Unknown"
      entry_id = c.get("id", "")
      username = f" @{c['username']}" if c.get("username") else ""
      lines.append(f"[{entry_type}] {name} (ID: {entry_id}){username}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_public_chats", e, ErrorCategory.SEARCH)


async def search_messages(args: dict[str, Any]) -> ToolResult:
  try:
    query = args.get("query", "")
    if not isinstance(query, str) or not query:
      return ToolResult(content="Search query is required", is_error=True)
    chat_id = opt_string(args, "chat_id")
    limit = opt_number(args, "limit", 20)

    result = await search_api.search_messages(query, chat_id, limit)
    if not result.data:
      return ToolResult(content=f'No messages found for "{query}".')

    lines = []
    for m in result.data:
      date = m.get("date")
      if date and isinstance(date, (int, float)):
        date_str = datetime.fromtimestamp(date, tz=UTC).isoformat()
      elif date:
        date_str = str(date)
      else:
        date_str = "unknown"
      msg_text = m.get("message", "")
      lines.append(f"[{m.get('id', '?')}] {date_str}: {msg_text}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_messages", e, ErrorCategory.SEARCH)


async def resolve_username(args: dict[str, Any]) -> ToolResult:
  try:
    username = args.get("username", "")
    if not isinstance(username, str) or not username:
      return ToolResult(content="Username is required", is_error=True)

    result = await search_api.resolve_username(username)
    if not result.data:
      return ToolResult(content=f"Username @{username.lstrip('@')} not found.")
    return ToolResult(content=json.dumps(result.data, indent=2, default=str))
  except Exception as e:
    return log_and_format_error("resolve_username", e, ErrorCategory.SEARCH)
