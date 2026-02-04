"""
Flag/manage tool handlers (mark read, flag, move, delete, archive).
"""

from __future__ import annotations

from typing import Any

from ..api import flag_api
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import opt_string, req_string, validate_uid_list


async def mark_read(args: dict[str, Any]) -> ToolResult:
  try:
    uids = validate_uid_list(args.get("message_ids"))
    folder = opt_string(args, "folder") or "INBOX"

    result = await flag_api.mark_read(uids, folder)
    if result:
      return ToolResult(content=f"Marked {len(uids)} message(s) as read.")
    return ToolResult(content="Failed to mark messages as read.", is_error=True)
  except Exception as e:
    return log_and_format_error("mark_read", e, ErrorCategory.FLAG)


async def mark_unread(args: dict[str, Any]) -> ToolResult:
  try:
    uids = validate_uid_list(args.get("message_ids"))
    folder = opt_string(args, "folder") or "INBOX"

    result = await flag_api.mark_unread(uids, folder)
    if result:
      return ToolResult(content=f"Marked {len(uids)} message(s) as unread.")
    return ToolResult(content="Failed to mark messages as unread.", is_error=True)
  except Exception as e:
    return log_and_format_error("mark_unread", e, ErrorCategory.FLAG)


async def flag_message(args: dict[str, Any]) -> ToolResult:
  try:
    uids = validate_uid_list(args.get("message_ids"))
    folder = opt_string(args, "folder") or "INBOX"

    result = await flag_api.flag_message(uids, folder)
    if result:
      return ToolResult(content=f"Flagged {len(uids)} message(s).")
    return ToolResult(content="Failed to flag messages.", is_error=True)
  except Exception as e:
    return log_and_format_error("flag_message", e, ErrorCategory.FLAG)


async def unflag_message(args: dict[str, Any]) -> ToolResult:
  try:
    uids = validate_uid_list(args.get("message_ids"))
    folder = opt_string(args, "folder") or "INBOX"

    result = await flag_api.unflag_message(uids, folder)
    if result:
      return ToolResult(content=f"Unflagged {len(uids)} message(s).")
    return ToolResult(content="Failed to unflag messages.", is_error=True)
  except Exception as e:
    return log_and_format_error("unflag_message", e, ErrorCategory.FLAG)


async def delete_message(args: dict[str, Any]) -> ToolResult:
  try:
    uids = validate_uid_list(args.get("message_ids"))
    folder = opt_string(args, "folder") or "INBOX"

    result = await flag_api.delete_message(uids, folder)
    if result:
      return ToolResult(content=f"Deleted {len(uids)} message(s) from {folder}.")
    return ToolResult(content="Failed to delete messages.", is_error=True)
  except Exception as e:
    return log_and_format_error("delete_message", e, ErrorCategory.FLAG)


async def move_message(args: dict[str, Any]) -> ToolResult:
  try:
    uids = validate_uid_list(args.get("message_ids"))
    destination = req_string(args, "destination")
    folder = opt_string(args, "folder") or "INBOX"

    result = await flag_api.move_message(uids, destination, folder)
    if result:
      return ToolResult(content=f"Moved {len(uids)} message(s) to {destination}.")
    return ToolResult(content="Failed to move messages.", is_error=True)
  except Exception as e:
    return log_and_format_error("move_message", e, ErrorCategory.FLAG)


async def archive_message(args: dict[str, Any]) -> ToolResult:
  try:
    uids = validate_uid_list(args.get("message_ids"))
    folder = opt_string(args, "folder") or "INBOX"

    result = await flag_api.archive_message(uids, folder)
    if result:
      return ToolResult(content=f"Archived {len(uids)} message(s).")
    return ToolResult(content="Failed to archive messages.", is_error=True)
  except Exception as e:
    return log_and_format_error("archive_message", e, ErrorCategory.FLAG)
