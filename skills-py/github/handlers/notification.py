"""Notification domain tool handlers."""

from __future__ import annotations

from typing import Any

from ..client.gh_client import get_client, run_sync
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import opt_boolean, opt_number, req_string


async def list_notifications(args: dict[str, Any]) -> ToolResult:
  try:
    all_notifs = opt_boolean(args, "all", False)
    limit = opt_number(args, "limit", 30)

    gh = get_client().gh
    user = await run_sync(gh.get_user)
    notifications = await run_sync(user.get_notifications, all=all_notifs)
    items = await run_sync(lambda: list(notifications[:limit]))

    if not items:
      return ToolResult(content="No notifications.")
    lines = []
    for n in items:
      reason = n.reason or ""
      repo_name = n.repository.full_name if n.repository else ""
      title = n.subject.title if n.subject else ""
      ntype = n.subject.type if n.subject else ""
      unread = "[unread]" if n.unread else "[read]"
      lines.append(f"{unread} [{repo_name}] {ntype}: {title} ({reason})")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_notifications", e, ErrorCategory.NOTIFY)


async def mark_notification_read(args: dict[str, Any]) -> ToolResult:
  try:
    thread_id = req_string(args, "thread_id")

    gh = get_client().gh
    user = await run_sync(gh.get_user)
    notification = await run_sync(user.get_notification, thread_id)
    await run_sync(notification.mark_as_read)
    return ToolResult(content=f"Notification {thread_id} marked as read.")
  except Exception as e:
    return log_and_format_error("mark_notification_read", e, ErrorCategory.NOTIFY)


async def mark_all_notifications_read(args: dict[str, Any]) -> ToolResult:
  try:
    gh = get_client().gh
    user = await run_sync(gh.get_user)
    await run_sync(user.mark_notifications_as_read)
    return ToolResult(content="All notifications marked as read.")
  except Exception as e:
    return log_and_format_error("mark_all_notifications_read", e, ErrorCategory.NOTIFY)
