"""
Settings domain tool handlers (mute, archive, privacy).

Ported from handlers/settings.ts.
"""

from __future__ import annotations

import json
from typing import Any

from ..api import settings_api
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import validate_id


async def mute_chat(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    mute_for = args.get("mute_for") if isinstance(args.get("mute_for"), (int, float)) else None

    await settings_api.mute_chat(str(chat_id), int(mute_for) if mute_for else None)
    return ToolResult(content=f"Chat {chat_id} muted.")
  except Exception as e:
    return log_and_format_error("mute_chat", e, ErrorCategory.CHAT)


async def unmute_chat(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    await settings_api.unmute_chat(str(chat_id))
    return ToolResult(content=f"Chat {chat_id} unmuted.")
  except Exception as e:
    return log_and_format_error("unmute_chat", e, ErrorCategory.CHAT)


async def archive_chat(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    await settings_api.archive_chat(str(chat_id))
    return ToolResult(content=f"Chat {chat_id} archived.")
  except Exception as e:
    return log_and_format_error("archive_chat", e, ErrorCategory.CHAT)


async def unarchive_chat(args: dict[str, Any]) -> ToolResult:
  try:
    chat_id = validate_id(args.get("chat_id"), "chat_id")
    await settings_api.unarchive_chat(str(chat_id))
    return ToolResult(content=f"Chat {chat_id} unarchived.")
  except Exception as e:
    return log_and_format_error("unarchive_chat", e, ErrorCategory.CHAT)


async def get_privacy_settings(args: dict[str, Any]) -> ToolResult:
  try:
    result = await settings_api.get_privacy_settings()
    if not result.data:
      return ToolResult(content="Unable to retrieve privacy settings.")
    return ToolResult(content=json.dumps(result.data, indent=2))
  except Exception as e:
    return log_and_format_error("get_privacy_settings", e, ErrorCategory.CHAT)


async def set_privacy_settings(args: dict[str, Any]) -> ToolResult:
  try:
    setting = args.get("setting", "")
    if not isinstance(setting, str) or not setting:
      return ToolResult(content="Setting name is required", is_error=True)
    value = args.get("value", "")
    if not isinstance(value, str) or not value:
      return ToolResult(content="Setting value is required", is_error=True)

    await settings_api.set_privacy_settings(setting, value)
    return ToolResult(content=f'Privacy setting "{setting}" updated to "{value}".')
  except Exception as e:
    return log_and_format_error("set_privacy_settings", e, ErrorCategory.CHAT)
