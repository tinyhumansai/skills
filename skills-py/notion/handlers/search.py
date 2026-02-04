"""Search/listing handlers — list all pages and databases."""

from __future__ import annotations

import logging
from typing import Any

from ..client import get_client
from ..helpers import (
  ToolResult,
  enforce_rate_limit,
  extract_title,
  format_api_error,
)

log = logging.getLogger("skill.notion.handlers.search")


async def notion_list_all_pages(args: dict[str, Any]) -> ToolResult:
  """List all pages accessible to the integration."""
  client = get_client()
  page_size = min(args.get("page_size", 20), 100)

  await enforce_rate_limit("read")

  try:
    response = await client.search(
      filter={"property": "object", "value": "page"},
      page_size=page_size,
    )
    results = response.get("results", [])

    if not results:
      return ToolResult(content="No pages found. Make sure pages are shared with your integration.")

    lines = [f"Found {len(results)} page(s):\n"]
    for page in results:
      title = extract_title(page)
      page_id = page.get("id", "")
      url = page.get("url", "")
      edited = page.get("last_edited_time", "")
      archived = page.get("archived", False)

      status = " [archived]" if archived else ""
      lines.append(f"  {title}{status}")
      lines.append(f"    ID: {page_id}")
      if url:
        lines.append(f"    URL: {url}")
      if edited:
        lines.append(f"    Last edited: {edited}")
      lines.append("")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return format_api_error("notion_list_all_pages", e)


async def notion_list_all_databases(args: dict[str, Any]) -> ToolResult:
  """List all databases accessible to the integration."""
  client = get_client()
  page_size = min(args.get("page_size", 20), 100)

  await enforce_rate_limit("read")

  try:
    response = await client.search(
      filter={"property": "object", "value": "database"},
      page_size=page_size,
    )
    results = response.get("results", [])

    if not results:
      return ToolResult(
        content="No databases found. Make sure databases are shared with your integration."
      )

    lines = [f"Found {len(results)} database(s):\n"]
    for db in results:
      title = extract_title(db)
      db_id = db.get("id", "")
      url = db.get("url", "")
      edited = db.get("last_edited_time", "")
      props = db.get("properties", {})

      lines.append(f"  {title}")
      lines.append(f"    ID: {db_id}")
      if url:
        lines.append(f"    URL: {url}")
      if edited:
        lines.append(f"    Last edited: {edited}")
      lines.append(f"    Properties: {', '.join(props.keys())}")
      lines.append("")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return format_api_error("notion_list_all_databases", e)
