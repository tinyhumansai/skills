"""User handlers — list and get users."""

from __future__ import annotations

import logging
from typing import Any

from ..client import get_client
from ..helpers import (
  ToolResult,
  enforce_rate_limit,
  format_api_error,
  format_user_summary,
)

log = logging.getLogger("skill.notion.handlers.users")


async def notion_list_users(args: dict[str, Any]) -> ToolResult:
  """List all workspace users."""
  client = get_client()
  page_size = min(args.get("page_size", 50), 100)

  await enforce_rate_limit("read")

  try:
    response = await client.users.list(page_size=page_size)
    results = response.get("results", [])

    if not results:
      return ToolResult(content="No users found.")

    lines = [f"Found {len(results)} user(s):\n"]
    for user in results:
      lines.append(format_user_summary(user))
      lines.append("")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return format_api_error("notion_list_users", e)


async def notion_get_user(args: dict[str, Any]) -> ToolResult:
  """Get a user by ID."""
  client = get_client()
  user_id = args.get("user_id", "")
  if not user_id:
    return ToolResult(content="user_id is required", is_error=True)

  await enforce_rate_limit("read")

  try:
    user = await client.users.retrieve(user_id=user_id)
    return ToolResult(content=format_user_summary(user))
  except Exception as e:
    return format_api_error("notion_get_user", e)
