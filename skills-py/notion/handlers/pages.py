"""Page handlers — search, get, create, update, delete pages."""

from __future__ import annotations

import logging
from typing import Any

from ..client import get_client
from ..helpers import (
  ToolResult,
  enforce_rate_limit,
  extract_title,
  format_api_error,
  format_page_summary,
  make_rich_text,
)

log = logging.getLogger("skill.notion.handlers.pages")


async def notion_search(args: dict[str, Any]) -> ToolResult:
  """Search pages and databases."""
  client = get_client()
  query = args.get("query", "")
  filter_type = args.get("filter")
  page_size = min(args.get("page_size", 20), 100)

  await enforce_rate_limit("read")

  try:
    kwargs: dict[str, Any] = {"page_size": page_size}
    if query:
      kwargs["query"] = query
    if filter_type:
      kwargs["filter"] = {"property": "object", "value": filter_type}

    response = await client.search(**kwargs)
    results = response.get("results", [])

    if not results:
      return ToolResult(content="No results found.")

    lines = [f"Found {len(results)} result(s):\n"]
    for item in results:
      obj_type = item.get("object", "unknown")
      title = extract_title(item)
      item_id = item.get("id", "")
      url = item.get("url", "")
      lines.append(f"  [{obj_type}] {title}")
      lines.append(f"    ID: {item_id}")
      if url:
        lines.append(f"    URL: {url}")
      lines.append("")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return format_api_error("notion_search", e)


async def notion_get_page(args: dict[str, Any]) -> ToolResult:
  """Get a page by ID."""
  client = get_client()
  page_id = args.get("page_id", "")
  if not page_id:
    return ToolResult(content="page_id is required", is_error=True)

  await enforce_rate_limit("read")

  try:
    page = await client.pages.retrieve(page_id=page_id)
    return ToolResult(content=format_page_summary(page))
  except Exception as e:
    return format_api_error("notion_get_page", e)


async def notion_create_page(args: dict[str, Any]) -> ToolResult:
  """Create a new page."""
  client = get_client()
  parent_id = args.get("parent_id", "")
  parent_type = args.get("parent_type", "page")
  title = args.get("title", "")
  content = args.get("content")
  extra_props = args.get("properties", {})

  if not parent_id:
    return ToolResult(content="parent_id is required", is_error=True)
  if not title:
    return ToolResult(content="title is required", is_error=True)

  await enforce_rate_limit("write")

  try:
    # Build parent
    parent = {"database_id": parent_id} if parent_type == "database" else {"page_id": parent_id}

    # Build properties
    properties: dict[str, Any] = {}
    if parent_type == "database":
      # For database entries, the title property is typically "Name"
      title_key = "Name"
      # Check if extra_props already has a title-type property
      if extra_props:
        properties.update(extra_props)
      if title_key not in properties:
        properties[title_key] = {"title": make_rich_text(title)}
    else:
      properties["title"] = {"title": make_rich_text(title)}
      if extra_props:
        properties.update(extra_props)

    # Build children blocks
    children: list[dict[str, Any]] = []
    if content:
      children.append(
        {
          "object": "block",
          "type": "paragraph",
          "paragraph": {"rich_text": make_rich_text(content)},
        }
      )

    kwargs: dict[str, Any] = {
      "parent": parent,
      "properties": properties,
    }
    if children:
      kwargs["children"] = children

    page = await client.pages.create(**kwargs)

    return ToolResult(content=f"Page created successfully.\n\n{format_page_summary(page)}")
  except Exception as e:
    return format_api_error("notion_create_page", e)


async def notion_update_page(args: dict[str, Any]) -> ToolResult:
  """Update a page's properties."""
  client = get_client()
  page_id = args.get("page_id", "")
  title = args.get("title")
  properties = args.get("properties", {})
  archived = args.get("archived")

  if not page_id:
    return ToolResult(content="page_id is required", is_error=True)

  await enforce_rate_limit("write")

  try:
    kwargs: dict[str, Any] = {"page_id": page_id}

    # Build properties update
    if title is not None:
      if not properties:
        properties = {}
      properties["title"] = {"title": make_rich_text(title)}

    if properties:
      kwargs["properties"] = properties
    if archived is not None:
      kwargs["archived"] = archived

    page = await client.pages.update(**kwargs)

    return ToolResult(content=f"Page updated successfully.\n\n{format_page_summary(page)}")
  except Exception as e:
    return format_api_error("notion_update_page", e)


async def notion_delete_page(args: dict[str, Any]) -> ToolResult:
  """Archive (soft-delete) a page."""
  client = get_client()
  page_id = args.get("page_id", "")
  if not page_id:
    return ToolResult(content="page_id is required", is_error=True)

  await enforce_rate_limit("write")

  try:
    await client.pages.update(page_id=page_id, archived=True)
    return ToolResult(content=f"Page {page_id} archived successfully.")
  except Exception as e:
    return format_api_error("notion_delete_page", e)
