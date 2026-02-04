"""Database handlers — query, get, create, update databases."""

from __future__ import annotations

import logging
from typing import Any

from ..client import get_client
from ..helpers import (
  ToolResult,
  enforce_rate_limit,
  extract_title,
  format_api_error,
  format_database_summary,
  make_rich_text,
)

log = logging.getLogger("skill.notion.handlers.databases")


async def notion_query_database(args: dict[str, Any]) -> ToolResult:
  """Query a database with optional filters and sorts."""
  client = get_client()
  database_id = args.get("database_id", "")
  filter_obj = args.get("filter")
  sorts = args.get("sorts")
  page_size = min(args.get("page_size", 20), 100)

  if not database_id:
    return ToolResult(content="database_id is required", is_error=True)

  await enforce_rate_limit("read")

  try:
    kwargs: dict[str, Any] = {
      "database_id": database_id,
      "page_size": page_size,
    }
    if filter_obj:
      kwargs["filter"] = filter_obj
    if sorts:
      kwargs["sorts"] = sorts

    response = await client.databases.query(**kwargs)
    results = response.get("results", [])

    if not results:
      return ToolResult(content="No entries found in this database.")

    lines = [f"Found {len(results)} entry/entries:\n"]
    for entry in results:
      title = extract_title(entry)
      entry_id = entry.get("id", "")
      url = entry.get("url", "")
      lines.append(f"  {title}")
      lines.append(f"    ID: {entry_id}")
      if url:
        lines.append(f"    URL: {url}")

      # Show a few key properties
      props = entry.get("properties", {})
      for prop_name, prop_val in list(props.items())[:5]:
        prop_type = prop_val.get("type", "")
        val_str = _format_property_value(prop_val, prop_type)
        if val_str:
          lines.append(f"    {prop_name}: {val_str}")
      lines.append("")

    return ToolResult(content="\n".join(lines))
  except Exception as e:
    return format_api_error("notion_query_database", e)


async def notion_get_database(args: dict[str, Any]) -> ToolResult:
  """Get database schema."""
  client = get_client()
  database_id = args.get("database_id", "")
  if not database_id:
    return ToolResult(content="database_id is required", is_error=True)

  await enforce_rate_limit("read")

  try:
    db = await client.databases.retrieve(database_id=database_id)
    summary = format_database_summary(db)

    # Add property schema details
    props = db.get("properties", {})
    if props:
      schema_lines = ["\n\nProperty Schema:"]
      for name, prop in props.items():
        prop_type = prop.get("type", "unknown")
        schema_lines.append(f"  {name}: {prop_type}")
      summary += "\n".join(schema_lines)

    return ToolResult(content=summary)
  except Exception as e:
    return format_api_error("notion_get_database", e)


async def notion_create_database(args: dict[str, Any]) -> ToolResult:
  """Create a new database in a parent page."""
  client = get_client()
  parent_id = args.get("parent_id", "")
  title = args.get("title", "")
  properties = args.get("properties", {})

  if not parent_id:
    return ToolResult(content="parent_id is required", is_error=True)
  if not title:
    return ToolResult(content="title is required", is_error=True)

  await enforce_rate_limit("write")

  try:
    # Always include a title property
    if "Name" not in properties:
      properties["Name"] = {"title": {}}

    db = await client.databases.create(
      parent={"page_id": parent_id},
      title=make_rich_text(title),
      properties=properties,
    )

    return ToolResult(content=f"Database created successfully.\n\n{format_database_summary(db)}")
  except Exception as e:
    return format_api_error("notion_create_database", e)


async def notion_update_database(args: dict[str, Any]) -> ToolResult:
  """Update a database's title, description, or properties."""
  client = get_client()
  database_id = args.get("database_id", "")
  title = args.get("title")
  description = args.get("description")
  properties = args.get("properties")

  if not database_id:
    return ToolResult(content="database_id is required", is_error=True)

  await enforce_rate_limit("write")

  try:
    kwargs: dict[str, Any] = {"database_id": database_id}
    if title is not None:
      kwargs["title"] = make_rich_text(title)
    if description is not None:
      kwargs["description"] = make_rich_text(description)
    if properties is not None:
      kwargs["properties"] = properties

    db = await client.databases.update(**kwargs)

    return ToolResult(content=f"Database updated successfully.\n\n{format_database_summary(db)}")
  except Exception as e:
    return format_api_error("notion_update_database", e)


def _format_property_value(prop: dict[str, Any], prop_type: str) -> str:
  """Format a property value for display."""
  if prop_type == "title":
    return "".join(rt.get("plain_text", "") for rt in prop.get("title", []))
  if prop_type == "rich_text":
    return "".join(rt.get("plain_text", "") for rt in prop.get("rich_text", []))
  if prop_type == "number":
    val = prop.get("number")
    return str(val) if val is not None else ""
  if prop_type == "select":
    sel = prop.get("select")
    return sel.get("name", "") if sel else ""
  if prop_type == "multi_select":
    items = prop.get("multi_select", [])
    return ", ".join(s.get("name", "") for s in items)
  if prop_type == "date":
    date_obj = prop.get("date")
    if date_obj:
      start = date_obj.get("start", "")
      end = date_obj.get("end", "")
      return f"{start} → {end}" if end else start
    return ""
  if prop_type == "checkbox":
    return str(prop.get("checkbox", False))
  if prop_type == "url":
    return prop.get("url", "") or ""
  if prop_type == "email":
    return prop.get("email", "") or ""
  if prop_type == "phone_number":
    return prop.get("phone_number", "") or ""
  if prop_type == "status":
    status = prop.get("status")
    return status.get("name", "") if status else ""
  return ""
