"""Message-related tool handlers."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..client.slack_client import get_client
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import ValidationError, validate_channel_id, validate_message_ts

log = logging.getLogger("skill.slack.handlers.message")


async def send_message(args: dict[str, Any]) -> ToolResult:
  """Send a message."""
  try:
    channel_id = args.get("channel_id", "")
    text = args.get("text", "").strip()
    thread_ts = args.get("thread_ts")
    validate_channel_id(channel_id)
    if not text:
      raise ValidationError("text is required")

    client = get_client()
    if not client:
      return ToolResult(content="Slack client not initialized", is_error=True)

    result = await client.chat_post_message(channel_id, text, thread_ts=thread_ts)
    message = result.get("message", {})

    return ToolResult(
      content=json.dumps(
        {
          "ts": message.get("ts"),
          "channel": message.get("channel"),
          "text": message.get("text"),
        },
        indent=2,
      )
    )

  except ValidationError as e:
    return ToolResult(content=str(e), is_error=True)
  except Exception as e:
    return log_and_format_error("send_message", e, ErrorCategory.MESSAGE)


async def get_messages(args: dict[str, Any]) -> ToolResult:
  """Get messages from a channel."""
  try:
    channel_id = args.get("channel_id", "")
    limit = args.get("limit", 50)
    oldest = args.get("oldest")
    latest = args.get("latest")
    validate_channel_id(channel_id)

    client = get_client()
    if not client:
      return ToolResult(content="Slack client not initialized", is_error=True)

    result = await client.conversations_history(
      channel_id,
      limit=min(limit, 200),
      oldest=oldest,
      latest=latest,
    )

    messages = []
    for msg in result.get("messages", []):
      messages.append(
        {
          "ts": msg.get("ts"),
          "user": msg.get("user"),
          "text": msg.get("text"),
          "type": msg.get("type"),
          "subtype": msg.get("subtype"),
        }
      )

    return ToolResult(content=json.dumps({"messages": messages}, indent=2))

  except ValidationError as e:
    return ToolResult(content=str(e), is_error=True)
  except Exception as e:
    return log_and_format_error("get_messages", e, ErrorCategory.MESSAGE)


async def edit_message(args: dict[str, Any]) -> ToolResult:
  """Edit a message."""
  try:
    channel_id = args.get("channel_id", "")
    message_ts = args.get("message_ts", "")
    text = args.get("text", "").strip()
    validate_channel_id(channel_id)
    validate_message_ts(message_ts)
    if not text:
      raise ValidationError("text is required")

    client = get_client()
    if not client:
      return ToolResult(content="Slack client not initialized", is_error=True)

    await client.chat_update(channel_id, message_ts, text)
    return ToolResult(content=f"Successfully updated message {message_ts}")

  except ValidationError as e:
    return ToolResult(content=str(e), is_error=True)
  except Exception as e:
    return log_and_format_error("edit_message", e, ErrorCategory.MESSAGE)


async def delete_message(args: dict[str, Any]) -> ToolResult:
  """Delete a message."""
  try:
    channel_id = args.get("channel_id", "")
    message_ts = args.get("message_ts", "")
    validate_channel_id(channel_id)
    validate_message_ts(message_ts)

    client = get_client()
    if not client:
      return ToolResult(content="Slack client not initialized", is_error=True)

    await client.chat_delete(channel_id, message_ts)
    return ToolResult(content=f"Successfully deleted message {message_ts}")

  except ValidationError as e:
    return ToolResult(content=str(e), is_error=True)
  except Exception as e:
    return log_and_format_error("delete_message", e, ErrorCategory.MESSAGE)


async def get_message_permalink(args: dict[str, Any]) -> ToolResult:
  """Get message permalink."""
  try:
    channel_id = args.get("channel_id", "")
    message_ts = args.get("message_ts", "")
    validate_channel_id(channel_id)
    validate_message_ts(message_ts)

    client = get_client()
    if not client:
      return ToolResult(content="Slack client not initialized", is_error=True)

    result = await client.chat_get_permalink(channel_id, message_ts)
    permalink = result.get("permalink", "")

    return ToolResult(content=json.dumps({"permalink": permalink}, indent=2))

  except ValidationError as e:
    return ToolResult(content=str(e), is_error=True)
  except Exception as e:
    return log_and_format_error("get_message_permalink", e, ErrorCategory.MESSAGE)
