"""Block handlers — get, list children, append, update, delete blocks, and convenience tools."""

from __future__ import annotations

import logging
from typing import Any

from ..client import get_client
from ..helpers import (
  ToolResult,
  enforce_rate_limit,
  extract_title,
  format_api_error,
  format_block_text,
  make_rich_text,
)

log = logging.getLogger("skill.notion.handlers.blocks")


async def notion_get_block(args: dict[str, Any]) -> ToolResult:
  """Get a single block by ID."""
  client = get_client()
  block_id = args.get("block_id", "")
  if not block_id:
    return ToolResult(content="block_id is required", is_error=True)

  await enforce_rate_limit("read")

  try:
    block = await client.blocks.retrieve(block_id=block_id)
    text = format_block_text(block)
    block_type = block.get("type", "unknown")
    has_children = block.get("has_children", False)
    lines = [
      f"Type: {block_type}",
      f"ID: {block.get('id', '')}",
      f"Has children: {has_children}",
      f"Content: {text}",
    ]
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return format_api_error("notion_get_block", e)


async def notion_get_block_children(args: dict[str, Any]) -> ToolResult:
  """List child blocks of a block or page."""
  client = get_client()
  block_id = args.get("block_id", "")
  page_size = min(args.get("page_size", 50), 100)

  if not block_id:
    return ToolResult(content="block_id is required", is_error=True)

  await enforce_rate_limit("read")

  try:
    response = await client.blocks.children.list(block_id=block_id, page_size=page_size)
    results = response.get("results", [])

    if not results:
      return ToolResult(content="No child blocks found.")

    lines = [f"Found {len(results)} block(s):\n"]
    for block in results:
      text = format_block_text(block)
      block_type = block.get("type", "unknown")
      bid = block.get("id", "")
      has_children = block.get("has_children", False)
      suffix = " [+children]" if has_children else ""
      lines.append(f"  [{block_type}]{suffix} {text}")
      lines.append(f"    ID: {bid}")
    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return format_api_error("notion_get_block_children", e)


async def notion_append_blocks(args: dict[str, Any]) -> ToolResult:
  """Append child blocks to a page or block."""
  client = get_client()
  block_id = args.get("block_id", "")
  children = args.get("children", [])

  if not block_id:
    return ToolResult(content="block_id is required", is_error=True)
  if not children:
    return ToolResult(content="children array is required", is_error=True)

  await enforce_rate_limit("write")

  try:
    response = await client.blocks.children.append(block_id=block_id, children=children)
    results = response.get("results", [])
    return ToolResult(content=f"Appended {len(results)} block(s) successfully.")
  except Exception as e:
    return format_api_error("notion_append_blocks", e)


async def notion_update_block(args: dict[str, Any]) -> ToolResult:
  """Update a block's content."""
  client = get_client()
  block_id = args.get("block_id", "")
  content = args.get("content", {})

  if not block_id:
    return ToolResult(content="block_id is required", is_error=True)
  if not content:
    return ToolResult(content="content object is required", is_error=True)

  await enforce_rate_limit("write")

  try:
    block = await client.blocks.update(block_id=block_id, **content)
    text = format_block_text(block)
    return ToolResult(content=f"Block updated successfully.\nContent: {text}")
  except Exception as e:
    return format_api_error("notion_update_block", e)


async def notion_delete_block(args: dict[str, Any]) -> ToolResult:
  """Delete a block."""
  client = get_client()
  block_id = args.get("block_id", "")
  if not block_id:
    return ToolResult(content="block_id is required", is_error=True)

  await enforce_rate_limit("write")

  try:
    await client.blocks.delete(block_id=block_id)
    return ToolResult(content=f"Block {block_id} deleted successfully.")
  except Exception as e:
    return format_api_error("notion_delete_block", e)


async def notion_get_page_content(args: dict[str, Any]) -> ToolResult:
  """Recursively fetch and render all blocks of a page as readable text."""
  client = get_client()
  page_id = args.get("page_id", "")
  max_depth = args.get("max_depth", 3)

  if not page_id:
    return ToolResult(content="page_id is required", is_error=True)

  await enforce_rate_limit("read")

  try:
    # Fetch page title first
    page = await client.pages.retrieve(page_id=page_id)
    title = extract_title(page)

    # Recursively fetch blocks
    lines = [f"# {title}\n"]
    await _fetch_blocks_recursive(client, page_id, lines, depth=0, max_depth=max_depth)

    if len(lines) == 1:
      lines.append("(empty page)")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return format_api_error("notion_get_page_content", e)


async def _fetch_blocks_recursive(
  client: Any,
  block_id: str,
  lines: list[str],
  depth: int,
  max_depth: int,
) -> None:
  """Recursively fetch blocks and render as text."""
  if depth >= max_depth:
    return

  await enforce_rate_limit("read")

  try:
    response = await client.blocks.children.list(block_id=block_id, page_size=100)
  except Exception:
    log.debug("Failed to fetch children for %s at depth %d", block_id, depth)
    return

  for block in response.get("results", []):
    text = format_block_text(block, indent=depth)
    if text:
      lines.append(text)

    # Recurse into children
    if block.get("has_children"):
      await _fetch_blocks_recursive(client, block["id"], lines, depth + 1, max_depth)


async def notion_append_text(args: dict[str, Any]) -> ToolResult:
  """Append a text block to a page (convenience wrapper)."""
  client = get_client()
  page_id = args.get("page_id", "")
  text = args.get("text", "")
  block_type = args.get("type", "paragraph")

  if not page_id:
    return ToolResult(content="page_id is required", is_error=True)
  if not text:
    return ToolResult(content="text is required", is_error=True)

  await enforce_rate_limit("write")

  try:
    block = {
      "object": "block",
      "type": block_type,
      block_type: {"rich_text": make_rich_text(text)},
    }

    # to_do blocks also need a "checked" field
    if block_type == "to_do":
      block[block_type]["checked"] = False

    await client.blocks.children.append(block_id=page_id, children=[block])

    return ToolResult(content=f"Text appended as {block_type} block.")
  except Exception as e:
    return format_api_error("notion_append_text", e)
