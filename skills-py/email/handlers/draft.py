"""
Draft tool handlers.
"""

from __future__ import annotations

from typing import Any

from ..api import draft_api
from ..helpers import ErrorCategory, ToolResult, format_email_summary, log_and_format_error
from ..validation import (
  opt_number,
  opt_string,
  opt_string_list,
  req_string,
  validate_email_list,
  validate_uid,
)


async def save_draft(args: dict[str, Any]) -> ToolResult:
  try:
    to = validate_email_list(args.get("to"), "to")
    subject = req_string(args, "subject")
    body = req_string(args, "body")
    html_body = opt_string(args, "html_body")
    cc = opt_string_list(args, "cc")
    bcc = opt_string_list(args, "bcc")

    result = await draft_api.save_draft(
      to=to,
      subject=subject,
      body=body,
      html_body=html_body,
      cc=cc,
      bcc=bcc,
    )
    if result:
      return ToolResult(content="Draft saved successfully.")
    return ToolResult(content="Failed to save draft.", is_error=True)
  except Exception as e:
    return log_and_format_error("save_draft", e, ErrorCategory.DRAFT)


async def list_drafts(args: dict[str, Any]) -> ToolResult:
  try:
    limit = opt_number(args, "limit", 20)

    drafts = await draft_api.list_drafts(limit)
    if not drafts:
      return ToolResult(content="No drafts found.")

    lines = [format_email_summary(d) for d in drafts]
    header = f"Drafts ({len(drafts)}):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_drafts", e, ErrorCategory.DRAFT)


async def update_draft(args: dict[str, Any]) -> ToolResult:
  try:
    uid = validate_uid(args.get("message_id"))
    to = None
    if args.get("to"):
      to = validate_email_list(args.get("to"), "to")
    subject = opt_string(args, "subject")
    body = opt_string(args, "body")
    html_body = opt_string(args, "html_body")

    result = await draft_api.update_draft(
      uid=uid,
      to=to,
      subject=subject,
      body=body,
      html_body=html_body,
    )
    if result:
      return ToolResult(content="Draft updated successfully.")
    return ToolResult(content="Failed to update draft.", is_error=True)
  except Exception as e:
    return log_and_format_error("update_draft", e, ErrorCategory.DRAFT)


async def delete_draft(args: dict[str, Any]) -> ToolResult:
  try:
    uid = validate_uid(args.get("message_id"))

    result = await draft_api.delete_draft(uid)
    if result:
      return ToolResult(content="Draft deleted.")
    return ToolResult(content="Failed to delete draft.", is_error=True)
  except Exception as e:
    return log_and_format_error("delete_draft", e, ErrorCategory.DRAFT)
