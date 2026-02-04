"""
Chat domain tool handlers.

Ported from handlers/chat.ts. Each handler validates args, calls the API,
and returns a ToolResult.
"""

from __future__ import annotations

from typing import Any

from ..api import chat_api
from ..helpers import ErrorCategory, ToolResult, format_entity, log_and_format_error
from ..validation import opt_number, validate_id


async def get_chats(args: dict[str, Any]) -> ToolResult:
  try:
    page = opt_number(args, "page", 1)
    page_size = opt_number(args, "page_size", 20)
    start = (page - 1) * page_size

    result = await chat_api.get_chats(page_size + start)
    paginated = result.data[start : start + page_size]

    if not paginated:
      return ToolResult(content="Page out of range.")

    lines = [f"Chat ID: {format_entity(c).id}, Title: {format_entity(c).name}" for c in paginated]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_chats", e, ErrorCategory.CHAT)


async def list_chats(args: dict[str, Any]) -> ToolResult:
  try:
    chat_type = args.get("chat_type") if isinstance(args.get("chat_type"), str) else None
    limit = opt_number(args, "limit", 20)

    result = await chat_api.get_chats(limit)
    chats = [c for c in result.data if c.type == chat_type] if chat_type else result.data

    if not chats:
      msg = f"No {chat_type} chats found." if chat_type else "No chats found."
      return ToolResult(content=msg)

    lines = []
    for c in chats:
      e = format_entity(c)
      username = f" @{e.username}" if e.username else ""
      lines.append(f"[{e.type}] {e.name} (ID: {e.id}){username}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_chats", e, ErrorCategory.CHAT)


async def get_chat(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    result = await chat_api.get_chat(str(chat_id))
    if not result.data:
      return ToolResult(content=f"Chat {chat_id} not found.", is_error=True)

    chat = result.data
    e = format_entity(chat)
    lines = [f"Chat ID: {e.id}", f"Name: {e.name}", f"Type: {e.type}"]
    if e.username:
      lines.append(f"Username: @{e.username}")
    if chat.participants_count:
      lines.append(f"Participants: {chat.participants_count}")
    lines.append(f"Unread: {chat.unread_count}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_chat", e, ErrorCategory.CHAT)


async def create_group(args: dict[str, Any]) -> ToolResult:
  try:
    title = args.get("title", "")
    if not isinstance(title, str) or not title:
      return ToolResult(content="Title is required", is_error=True)
    user_ids = (
      [str(u) for u in args.get("user_ids", [])] if isinstance(args.get("user_ids"), list) else []
    )
    if not user_ids:
      return ToolResult(content="At least one user ID is required", is_error=True)

    result = await chat_api.create_group(title, user_ids)
    return ToolResult(
      content=f'Group "{title}" created successfully.'
      if result.data
      else f'Failed to create group "{title}".'
    )
  except Exception as e:
    return log_and_format_error("create_group", e, ErrorCategory.GROUP)


async def invite_to_group(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    user_ids = (
      [str(u) for u in args.get("user_ids", [])] if isinstance(args.get("user_ids"), list) else []
    )
    if not user_ids:
      return ToolResult(content="At least one user ID is required", is_error=True)

    await chat_api.invite_to_group(str(chat_id), user_ids)
    return ToolResult(content=f"Invited {len(user_ids)} user(s) to chat {chat_id}.")
  except Exception as e:
    return log_and_format_error("invite_to_group", e, ErrorCategory.GROUP)


async def create_channel(args: dict[str, Any]) -> ToolResult:
  try:
    title = args.get("title", "")
    if not isinstance(title, str) or not title:
      return ToolResult(content="Title is required", is_error=True)
    description = args.get("description") if isinstance(args.get("description"), str) else None
    megagroup_val = args.get("megagroup")
    megagroup = bool(megagroup_val) if isinstance(megagroup_val, bool) else False

    result = await chat_api.create_channel(title, description, megagroup)
    return ToolResult(
      content=f'Channel "{title}" created successfully.'
      if result.data
      else f'Failed to create channel "{title}".'
    )
  except Exception as e:
    return log_and_format_error("create_channel", e, ErrorCategory.CHAT)


async def edit_chat_title(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    new_title = args.get("new_title", "")
    if not isinstance(new_title, str) or not new_title:
      return ToolResult(content="New title is required", is_error=True)

    await chat_api.edit_chat_title(str(chat_id), new_title)
    return ToolResult(content=f'Chat title updated to "{new_title}".')
  except Exception as e:
    return log_and_format_error("edit_chat_title", e, ErrorCategory.CHAT)


async def delete_chat_photo(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    await chat_api.delete_chat_photo(str(chat_id))
    return ToolResult(content="Chat photo deleted.")
  except Exception as e:
    return log_and_format_error("delete_chat_photo", e, ErrorCategory.CHAT)


async def leave_chat(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    await chat_api.leave_chat(str(chat_id))
    return ToolResult(content=f"Left chat {chat_id}.")
  except Exception as e:
    return log_and_format_error("leave_chat", e, ErrorCategory.CHAT)


async def get_invite_link(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    result = await chat_api.get_invite_link(str(chat_id))
    return ToolResult(
      content=f"Invite link: {result.data}" if result.data else "Failed to get invite link."
    )
  except Exception as e:
    return log_and_format_error("get_invite_link", e, ErrorCategory.CHAT)


async def export_chat_invite(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    expire_date = (
      args.get("expire_date") if isinstance(args.get("expire_date"), (int, float)) else None
    )
    usage_limit = (
      args.get("usage_limit") if isinstance(args.get("usage_limit"), (int, float)) else None
    )

    result = await chat_api.export_chat_invite(
      str(chat_id),
      int(expire_date) if expire_date else None,
      int(usage_limit) if usage_limit else None,
    )
    return ToolResult(
      content=f"Invite link: {result.data}" if result.data else "Failed to export invite link."
    )
  except Exception as e:
    return log_and_format_error("export_chat_invite", e, ErrorCategory.CHAT)


async def import_chat_invite(args: dict[str, Any]) -> ToolResult:
  try:
    invite_hash = args.get("invite_hash", "")
    if not isinstance(invite_hash, str) or not invite_hash:
      return ToolResult(content="Invite hash is required", is_error=True)

    await chat_api.import_chat_invite(invite_hash)
    return ToolResult(content="Successfully joined chat via invite.")
  except Exception as e:
    return log_and_format_error("import_chat_invite", e, ErrorCategory.CHAT)


async def join_chat_by_link(args: dict[str, Any]) -> ToolResult:
  try:
    invite_link = args.get("invite_link", "")
    if not isinstance(invite_link, str) or not invite_link:
      return ToolResult(content="Invite link is required", is_error=True)

    await chat_api.join_chat_by_link(invite_link)
    return ToolResult(content="Successfully joined chat via link.")
  except Exception as e:
    return log_and_format_error("join_chat_by_link", e, ErrorCategory.CHAT)


async def subscribe_public_channel(args: dict[str, Any]) -> ToolResult:
  try:
    username = args.get("username", "")
    if not isinstance(username, str) or not username:
      return ToolResult(content="Username is required", is_error=True)

    await chat_api.subscribe_public_channel(username)
    return ToolResult(content=f"Subscribed to @{username.lstrip('@')}.")
  except Exception as e:
    return log_and_format_error("subscribe_public_channel", e, ErrorCategory.CHAT)
