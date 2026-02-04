"""
Admin domain tool handlers.

Ported from handlers/admin.ts.
"""

from __future__ import annotations

import json
from typing import Any

from ..api import admin_api
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import opt_number, opt_string, validate_id


async def get_participants(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    limit = opt_number(args, "limit", 100)
    filter_type = opt_string(args, "filter") or "recent"

    result = await admin_api.get_participants(str(chat_id), limit, filter_type)
    if not result.data:
      return ToolResult(content=f"No participants found in chat {chat_id}.")

    lines = []
    for p in result.data:
      user = p.get("user")
      if user:
        name = " ".join(part for part in [user.first_name, user.last_name] if part) or "Unknown"
        username = f" @{user.username}" if user.username else ""
        lines.append(f"{name} (ID: {user.id}){username}")
      else:
        lines.append(f"Unknown participant: {p.get('participant', 'N/A')}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_participants", e, ErrorCategory.ADMIN)


async def get_admins(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    result = await admin_api.get_admins(str(chat_id))

    if not result.data:
      return ToolResult(content=f"No admins found in chat {chat_id}.")

    lines = []
    for a in result.data:
      user = a.get("user")
      if user:
        name = " ".join(part for part in [user.first_name, user.last_name] if part) or "Unknown"
        username = f" @{user.username}" if user.username else ""
        lines.append(f"{name} (ID: {user.id}){username}")
      else:
        lines.append(f"Unknown admin: {a.get('participant', 'N/A')}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_admins", e, ErrorCategory.ADMIN)


async def get_banned_users(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    limit = opt_number(args, "limit", 100)

    result = await admin_api.get_banned_users(str(chat_id), limit)
    if not result.data:
      return ToolResult(content=f"No banned users in chat {chat_id}.")

    lines = []
    for u in result.data:
      user = u.get("user")
      if user:
        lines.append(f"{user.first_name} (ID: {user.id})")
      else:
        lines.append(f"Unknown banned user: {u.get('participant', 'N/A')}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_banned_users", e, ErrorCategory.ADMIN)


async def promote_admin(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    user_id = validate_id(args.get("user_id"), "user_id")
    title = opt_string(args, "title")

    await admin_api.promote_admin(str(chat_id), str(user_id), title)
    return ToolResult(content=f"User {user_id} promoted to admin in chat {chat_id}.")
  except Exception as e:
    return log_and_format_error("promote_admin", e, ErrorCategory.ADMIN)


async def demote_admin(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    user_id = validate_id(args.get("user_id"), "user_id")

    await admin_api.demote_admin(str(chat_id), str(user_id))
    return ToolResult(content=f"User {user_id} demoted from admin in chat {chat_id}.")
  except Exception as e:
    return log_and_format_error("demote_admin", e, ErrorCategory.ADMIN)


async def ban_user(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    user_id = validate_id(args.get("user_id"), "user_id")
    until_date = (
      args.get("until_date") if isinstance(args.get("until_date"), (int, float)) else None
    )

    await admin_api.ban_user(str(chat_id), str(user_id), int(until_date) if until_date else None)
    return ToolResult(content=f"User {user_id} banned from chat {chat_id}.")
  except Exception as e:
    return log_and_format_error("ban_user", e, ErrorCategory.ADMIN)


async def unban_user(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    user_id = validate_id(args.get("user_id"), "user_id")

    await admin_api.unban_user(str(chat_id), str(user_id))
    return ToolResult(content=f"User {user_id} unbanned in chat {chat_id}.")
  except Exception as e:
    return log_and_format_error("unban_user", e, ErrorCategory.ADMIN)


async def get_recent_actions(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    limit = opt_number(args, "limit", 20)

    result = await admin_api.get_recent_actions(str(chat_id), limit)
    if not result.data:
      return ToolResult(content=f"No recent admin actions in chat {chat_id}.")
    return ToolResult(content="\n".join(json.dumps(a) for a in result.data))
  except Exception as e:
    return log_and_format_error("get_recent_actions", e, ErrorCategory.ADMIN)
