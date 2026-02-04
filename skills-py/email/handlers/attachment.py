"""
Attachment tool handlers.
"""

from __future__ import annotations

from typing import Any

from ..api import attachment_api
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import opt_number, opt_string, validate_uid


async def list_attachments(args: dict[str, Any]) -> ToolResult:
  try:
    uid = validate_uid(args.get("message_id"))
    folder = opt_string(args, "folder") or "INBOX"

    attachments = await attachment_api.list_attachments(uid, folder)
    if not attachments:
      return ToolResult(content=f"No attachments on message UID {uid}.")

    lines = []
    for att in attachments:
      size_str = _format_size(att.size)
      lines.append(f"[{att.index}] {att.filename} ({att.content_type}, {size_str})")

    header = f"Attachments on message UID {uid} ({len(attachments)}):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_attachments", e, ErrorCategory.ATTACH)


async def get_attachment_info(args: dict[str, Any]) -> ToolResult:
  try:
    uid = validate_uid(args.get("message_id"))
    index = opt_number(args, "attachment_index", 0)
    folder = opt_string(args, "folder") or "INBOX"

    att = await attachment_api.get_attachment_info(uid, index, folder)
    if not att:
      return ToolResult(
        content=f"Attachment index {index} not found on message UID {uid}.",
        is_error=True,
      )

    lines = [
      f"Filename: {att.filename}",
      f"Content-Type: {att.content_type}",
      f"Size: {_format_size(att.size)}",
      f"Index: {att.index}",
    ]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_attachment_info", e, ErrorCategory.ATTACH)


async def save_attachment(args: dict[str, Any]) -> ToolResult:
  try:
    uid = validate_uid(args.get("message_id"))
    index = opt_number(args, "attachment_index", 0)
    folder = opt_string(args, "folder") or "INBOX"
    filename = opt_string(args, "filename")

    path = await attachment_api.save_attachment(uid, index, folder, filename)
    if path:
      return ToolResult(content=f"Attachment saved to: {path}")
    return ToolResult(content="Failed to save attachment.", is_error=True)
  except Exception as e:
    return log_and_format_error("save_attachment", e, ErrorCategory.ATTACH)


def _format_size(size: int) -> str:
  if size < 1024:
    return f"{size} B"
  if size < 1024 * 1024:
    return f"{size / 1024:.1f} KB"
  return f"{size / (1024 * 1024):.1f} MB"
