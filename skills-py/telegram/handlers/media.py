"""
Media, profile, and bot tool handlers.

Ported from handlers/media.ts.
"""

from __future__ import annotations

import json
from typing import Any

from ..api import settings_api
from ..helpers import ErrorCategory, ToolResult, format_entity, log_and_format_error
from ..state import store
from ..validation import opt_number, opt_string, validate_id


async def get_me(args: dict[str, Any]) -> ToolResult:
  try:
    result = await settings_api.get_me()
    if not result.data:
      return ToolResult(content="Unable to retrieve current user info.", is_error=True)

    user = result.data
    e = format_entity(user)
    lines = [f"Name: {e.name}", f"ID: {e.id}", f"Type: {e.type}"]
    if e.username:
      lines.append(f"Username: @{e.username}")
    if e.phone:
      lines.append(f"Phone: {e.phone}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return log_and_format_error("get_me", e, ErrorCategory.PROFILE)


async def update_profile(args: dict[str, Any]) -> ToolResult:
  try:
    first_name = opt_string(args, "first_name")
    last_name = opt_string(args, "last_name")
    bio = opt_string(args, "bio")

    await settings_api.update_profile(first_name, last_name, bio)
    return ToolResult(content="Profile updated successfully.")
  except Exception as e:
    return log_and_format_error("update_profile", e, ErrorCategory.PROFILE)


async def get_user_photos(args: dict[str, Any]) -> ToolResult:
  try:
    user_id = validate_id(args.get("user_id"), "user_id")
    limit = opt_number(args, "limit", 20)

    result = await settings_api.get_user_photos(str(user_id), limit)
    if not result.data:
      return ToolResult(content=f"No photos found for user {user_id}.")
    return ToolResult(content="\n".join(str(p) for p in result.data))
  except Exception as e:
    return log_and_format_error("get_user_photos", e, ErrorCategory.MEDIA)


async def get_user_status(args: dict[str, Any]) -> ToolResult:
  try:
    user_id = validate_id(args.get("user_id"), "user_id")
    result = await settings_api.get_user_status(str(user_id))
    return ToolResult(
      content=str(result.data) if result.data else f"Status for user {user_id}: unknown"
    )
  except Exception as e:
    return log_and_format_error("get_user_status", e, ErrorCategory.PROFILE)


async def set_profile_photo(args: dict[str, Any]) -> ToolResult:
  try:
    file_path = opt_string(args, "file_path")
    url = opt_string(args, "url")

    await settings_api.set_profile_photo(file_path, url)
    return ToolResult(content="Profile photo updated.")
  except Exception as e:
    return log_and_format_error("set_profile_photo", e, ErrorCategory.MEDIA)


async def delete_profile_photo(args: dict[str, Any]) -> ToolResult:
  try:
    photo_id = opt_string(args, "photo_id")
    await settings_api.delete_profile_photo(photo_id)
    return ToolResult(content="Profile photo deleted.")
  except Exception as e:
    return log_and_format_error("delete_profile_photo", e, ErrorCategory.MEDIA)


async def edit_chat_photo(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    file_path = opt_string(args, "file_path")

    await settings_api.edit_chat_photo(str(chat_id), file_path)
    return ToolResult(content="Chat photo updated.")
  except Exception as e:
    return log_and_format_error("edit_chat_photo", e, ErrorCategory.MEDIA)


async def get_media_info(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    message_id = args.get("message_id")
    if not isinstance(message_id, (int, float)):
      message_id = 0

    state = store.get_state()
    chat_msgs = state.messages.get(str(chat_id), {})
    msg = chat_msgs.get(str(int(message_id)))

    if not msg:
      return ToolResult(content=f"Message {message_id} not found in chat {chat_id}.")
    if not msg.media:
      return ToolResult(content=f"Message {message_id} has no media.")
    return ToolResult(content=f"Media type: {msg.media.get('type', 'unknown')}")
  except Exception as e:
    return log_and_format_error("get_media_info", e, ErrorCategory.MEDIA)


async def get_bot_info(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    result = await settings_api.get_bot_info(str(chat_id))
    if not result.data:
      return ToolResult(content=f"Bot info for {chat_id}: not available")
    return ToolResult(content=json.dumps(result.data))
  except Exception as e:
    return log_and_format_error("get_bot_info", e, ErrorCategory.PROFILE)


async def set_bot_commands(args: dict[str, Any]) -> ToolResult:
  try:
    commands = args.get("commands", [])
    if not isinstance(commands, list):
      commands = []
    chat_id = opt_string(args, "chat_id")

    cmd_list = [
      {
        "command": str(c.get("command", "")),
        "description": str(c.get("description", "")),
      }
      for c in commands
    ]

    await settings_api.set_bot_commands(cmd_list, chat_id)
    return ToolResult(content=f"{len(cmd_list)} bot commands set.")
  except Exception as e:
    return log_and_format_error("set_bot_commands", e, ErrorCategory.PROFILE)
