"""
Send/reply/forward tool handlers.
"""

from __future__ import annotations

from typing import Any

from ..api import send_api
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import (
  opt_boolean,
  opt_string,
  opt_string_list,
  req_string,
  validate_email_list,
  validate_uid,
)


async def send_email(args: dict[str, Any]) -> ToolResult:
  try:
    to = validate_email_list(args.get("to"), "to")
    subject = req_string(args, "subject")
    body = req_string(args, "body")
    html_body = opt_string(args, "html_body")
    cc = opt_string_list(args, "cc")
    bcc = opt_string_list(args, "bcc")
    reply_to = opt_string(args, "reply_to")

    result = await send_api.send_new_email(
      to=to,
      subject=subject,
      body=body,
      html_body=html_body,
      cc=cc,
      bcc=bcc,
      reply_to=reply_to,
    )
    if result:
      return ToolResult(content=f"Email sent to {', '.join(to)}.")
    return ToolResult(content="Failed to send email.", is_error=True)
  except Exception as e:
    return log_and_format_error("send_email", e, ErrorCategory.SEND)


async def reply_to_email(args: dict[str, Any]) -> ToolResult:
  try:
    uid = validate_uid(args.get("message_id"))
    body = req_string(args, "body")
    folder = opt_string(args, "folder") or "INBOX"
    reply_all = opt_boolean(args, "reply_all", False)
    html_body = opt_string(args, "html_body")

    result = await send_api.reply_to_email(
      uid=uid,
      body=body,
      folder=folder,
      reply_all=reply_all,
      html_body=html_body,
    )
    if result:
      mode = "all" if reply_all else "sender"
      return ToolResult(content=f"Reply sent to {mode}.")
    return ToolResult(content="Failed to send reply.", is_error=True)
  except Exception as e:
    return log_and_format_error("reply_to_email", e, ErrorCategory.SEND)


async def forward_email(args: dict[str, Any]) -> ToolResult:
  try:
    uid = validate_uid(args.get("message_id"))
    to = validate_email_list(args.get("to"), "to")
    folder = opt_string(args, "folder") or "INBOX"
    body = opt_string(args, "body")
    html_body = opt_string(args, "html_body")

    result = await send_api.forward_email(
      uid=uid,
      to=to,
      folder=folder,
      body=body,
      html_body=html_body,
    )
    if result:
      return ToolResult(content=f"Email forwarded to {', '.join(to)}.")
    return ToolResult(content="Failed to forward email.", is_error=True)
  except Exception as e:
    return log_and_format_error("forward_email", e, ErrorCategory.SEND)
