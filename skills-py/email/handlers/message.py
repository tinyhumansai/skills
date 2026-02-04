"""
Message read/list/search tool handlers.
"""

from __future__ import annotations

from typing import Any

from ..api import message_api
from ..helpers import (
  ErrorCategory,
  ToolResult,
  format_email_detail,
  format_email_summary,
  log_and_format_error,
)
from ..validation import opt_number, opt_string, validate_uid


async def list_messages(args: dict[str, Any]) -> ToolResult:
  try:
    folder = opt_string(args, "folder") or "INBOX"
    limit = opt_number(args, "limit", 20)
    offset = opt_number(args, "offset", 0)

    messages = await message_api.list_messages(folder, limit, offset)
    if not messages:
      return ToolResult(content=f"No messages in {folder}.")

    lines = [format_email_summary(m) for m in messages]
    header = f"Messages in {folder} ({len(messages)} shown):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_messages", e, ErrorCategory.MSG)


async def get_message(args: dict[str, Any]) -> ToolResult:
  try:
    uid = validate_uid(args.get("message_id"))
    folder = opt_string(args, "folder") or "INBOX"
    fmt = opt_string(args, "format") or "text"

    email = await message_api.get_message(uid, folder, fmt)
    if not email:
      return ToolResult(content=f"Message UID {uid} not found in {folder}.", is_error=True)

    return ToolResult(content=format_email_detail(email))
  except Exception as e:
    return log_and_format_error("get_message", e, ErrorCategory.MSG)


async def search_messages(args: dict[str, Any]) -> ToolResult:
  try:
    query = opt_string(args, "query") or ""
    folder = opt_string(args, "folder")
    limit = opt_number(args, "limit", 20)
    from_addr = opt_string(args, "from_addr")
    to_addr = opt_string(args, "to_addr")
    subject = opt_string(args, "subject")
    since = opt_string(args, "since")
    before = opt_string(args, "before")
    has_attachment = (
      args.get("has_attachment") if isinstance(args.get("has_attachment"), bool) else None
    )

    messages = await message_api.search_messages(
      query,
      folder,
      limit,
      from_addr=from_addr,
      to_addr=to_addr,
      subject=subject,
      since=since,
      before=before,
      has_attachment=has_attachment,
    )
    if not messages:
      return ToolResult(content="No messages match the search criteria.")

    lines = [format_email_summary(m) for m in messages]
    header = f"Search results ({len(messages)} found):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_messages", e, ErrorCategory.SEARCH)


async def get_unread_messages(args: dict[str, Any]) -> ToolResult:
  try:
    folder = opt_string(args, "folder") or "INBOX"
    limit = opt_number(args, "limit", 20)

    messages = await message_api.get_unread_messages(folder, limit)
    if not messages:
      return ToolResult(content=f"No unread messages in {folder}.")

    lines = [format_email_summary(m) for m in messages]
    header = f"Unread messages in {folder} ({len(messages)}):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_unread_messages", e, ErrorCategory.MSG)


async def get_thread(args: dict[str, Any]) -> ToolResult:
  try:
    uid = validate_uid(args.get("message_id"))
    folder = opt_string(args, "folder") or "INBOX"

    messages = await message_api.get_thread(uid, folder)
    if not messages:
      return ToolResult(content=f"No thread found for message UID {uid}.")

    lines = [format_email_summary(m) for m in messages]
    header = f"Thread ({len(messages)} messages):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_thread", e, ErrorCategory.MSG)


async def count_messages(args: dict[str, Any]) -> ToolResult:
  try:
    folder = opt_string(args, "folder") or "INBOX"
    count = await message_api.count_folder_messages(folder)
    return ToolResult(content=f"{folder}: {count} messages")
  except Exception as e:
    return log_and_format_error("count_messages", e, ErrorCategory.MSG)


async def get_recent_messages(args: dict[str, Any]) -> ToolResult:
  try:
    hours = opt_number(args, "hours", 24)
    folder = opt_string(args, "folder") or "INBOX"
    limit = opt_number(args, "limit", 20)

    messages = await message_api.get_recent_messages(hours, folder, limit)
    if not messages:
      return ToolResult(content=f"No messages in the last {hours} hours in {folder}.")

    lines = [format_email_summary(m) for m in messages]
    header = f"Messages from last {hours}h in {folder} ({len(messages)}):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_recent_messages", e, ErrorCategory.MSG)
