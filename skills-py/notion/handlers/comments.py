"""Comment handlers — create and list comments."""

from __future__ import annotations

import logging
from typing import Any

from ..client import get_client
from ..helpers import (
  ToolResult,
  _rich_text_to_str,
  enforce_rate_limit,
  format_api_error,
  make_rich_text,
)

log = logging.getLogger("skill.notion.handlers.comments")


async def notion_create_comment(args: dict[str, Any]) -> ToolResult:
  """Create a comment on a page."""
  client = get_client()
  parent_id = args.get("parent_id", "")
  text = args.get("text", "")

  if not parent_id:
    return ToolResult(content="parent_id is required", is_error=True)
  if not text:
    return ToolResult(content="text is required", is_error=True)

  await enforce_rate_limit("write")

  try:
    comment = await client.comments.create(
      parent={"page_id": parent_id},
      rich_text=make_rich_text(text),
    )
    comment_id = comment.get("id", "")
    return ToolResult(content=f"Comment created successfully (ID: {comment_id}).")
  except Exception as e:
    return format_api_error("notion_create_comment", e)


async def notion_list_comments(args: dict[str, Any]) -> ToolResult:
  """List comments on a page or block."""
  client = get_client()
  block_id = args.get("block_id", "")
  page_size = min(args.get("page_size", 20), 100)

  if not block_id:
    return ToolResult(content="block_id is required", is_error=True)

  await enforce_rate_limit("read")

  try:
    response = await client.comments.list(block_id=block_id, page_size=page_size)
    results = response.get("results", [])

    if not results:
      return ToolResult(content="No comments found.")

    lines = [f"Found {len(results)} comment(s):\n"]
    for comment in results:
      comment_id = comment.get("id", "")
      created_by = comment.get("created_by", {})
      author = created_by.get("name", created_by.get("id", "Unknown"))
      created_time = comment.get("created_time", "")
      text = _rich_text_to_str(comment.get("rich_text", []))

      lines.append(f"  [{created_time}] {author}:")
      lines.append(f"    {text}")
      lines.append(f"    ID: {comment_id}")
      lines.append("")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return format_api_error("notion_list_comments", e)
