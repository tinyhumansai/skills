"""Search-related tool handlers."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..client.slack_client import get_client
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import ValidationError

log = logging.getLogger("skill.slack.handlers.search")


async def search_messages(args: dict[str, Any]) -> ToolResult:
  """Search messages."""
  try:
    query = args.get("query", "").strip()
    count = args.get("count", 20)
    if not query:
      raise ValidationError("query is required")

    client = get_client()
    if not client:
      return ToolResult(content="Slack client not initialized", is_error=True)

    result = await client.search_messages(query, count=min(count, 100))
    matches = result.get("messages", {}).get("matches", [])

    results = []
    for match in matches[:count]:
      results.append(
        {
          "ts": match.get("ts"),
          "channel": match.get("channel", {}).get("name", ""),
          "user": match.get("user", ""),
          "text": match.get("text", ""),
          "permalink": match.get("permalink", ""),
        }
      )

    return ToolResult(content=json.dumps({"results": results}, indent=2))

  except ValidationError as e:
    return ToolResult(content=str(e), is_error=True)
  except Exception as e:
    return log_and_format_error("search_messages", e, ErrorCategory.SEARCH)


async def search_all(args: dict[str, Any]) -> ToolResult:
  """Search messages and files."""
  try:
    query = args.get("query", "").strip()
    count = args.get("count", 20)
    if not query:
      raise ValidationError("query is required")

    client = get_client()
    if not client:
      return ToolResult(content="Slack client not initialized", is_error=True)

    result = await client.search_all(query, count=min(count, 100))
    messages = result.get("messages", {}).get("matches", [])
    files = result.get("files", {}).get("matches", [])

    message_results = []
    for match in messages[:count]:
      message_results.append(
        {
          "ts": match.get("ts"),
          "channel": match.get("channel", {}).get("name", ""),
          "user": match.get("user", ""),
          "text": match.get("text", ""),
          "permalink": match.get("permalink", ""),
        }
      )

    file_results = []
    for match in files[:count]:
      file_results.append(
        {
          "id": match.get("id"),
          "name": match.get("name", ""),
          "title": match.get("title", ""),
          "permalink": match.get("permalink", ""),
        }
      )

    return ToolResult(
      content=json.dumps(
        {
          "messages": message_results,
          "files": file_results,
        },
        indent=2,
      )
    )

  except ValidationError as e:
    return ToolResult(content=str(e), is_error=True)
  except Exception as e:
    return log_and_format_error("search_all", e, ErrorCategory.SEARCH)
