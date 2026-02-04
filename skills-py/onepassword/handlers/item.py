"""
1Password item management tool handlers.
"""

from __future__ import annotations

from typing import Any

from ..api import (
  get_field,
  get_item,
  get_password,
  list_items,
  search_items,
)
from ..helpers import (
  ErrorCategory,
  ToolResult,
  format_item_detail,
  format_item_summary,
  log_and_format_error,
)
from ..validation import opt_string, require_string


async def list_items_handler(args: dict[str, Any]) -> ToolResult:
  try:
    vault = opt_string(args, "vault")
    categories = args.get("categories")

    items = await list_items(vault=vault, categories=categories)
    if not items:
      return ToolResult(content="No items found.")

    lines = [format_item_summary(item) for item in items]
    header = f"Items ({len(items)}):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_items", e, ErrorCategory.ITEM)


async def get_item_handler(args: dict[str, Any]) -> ToolResult:
  try:
    item_id = opt_string(args, "item_id")
    item_name = opt_string(args, "item_name")
    vault = opt_string(args, "vault")

    if not item_id and not item_name:
      return ToolResult(
        content="Either item_id or item_name must be provided",
        is_error=True,
      )

    item = await get_item(item_id=item_id, item_name=item_name, vault=vault)
    return ToolResult(content=format_item_detail(item))
  except Exception as e:
    return log_and_format_error("get_item", e, ErrorCategory.ITEM)


async def get_password_handler(args: dict[str, Any]) -> ToolResult:
  try:
    item_id = opt_string(args, "item_id")
    item_name = opt_string(args, "item_name")
    vault = opt_string(args, "vault")

    if not item_id and not item_name:
      return ToolResult(
        content="Either item_id or item_name must be provided",
        is_error=True,
      )

    password = await get_password(item_id=item_id, item_name=item_name, vault=vault)
    return ToolResult(content=password)
  except Exception as e:
    return log_and_format_error("get_password", e, ErrorCategory.FIELD)


async def get_field_handler(args: dict[str, Any]) -> ToolResult:
  try:
    item_id = opt_string(args, "item_id")
    item_name = opt_string(args, "item_name")
    field_label = require_string(args, "field_label")
    vault = opt_string(args, "vault")

    if not item_id and not item_name:
      return ToolResult(
        content="Either item_id or item_name must be provided",
        is_error=True,
      )

    value = await get_field(
      item_id=item_id,
      item_name=item_name,
      field_label=field_label,
      vault=vault,
    )
    return ToolResult(content=value)
  except Exception as e:
    return log_and_format_error("get_field", e, ErrorCategory.FIELD)


async def search_items_handler(args: dict[str, Any]) -> ToolResult:
  try:
    query = require_string(args, "query")
    vault = opt_string(args, "vault")

    items = await search_items(query=query, vault=vault)
    if not items:
      return ToolResult(content=f"No items found matching '{query}'.")

    lines = [format_item_summary(item) for item in items]
    header = f"Search results for '{query}' ({len(items)}):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_items", e, ErrorCategory.ITEM)
