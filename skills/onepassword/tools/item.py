"""
1Password item management tools.
"""

from __future__ import annotations

from mcp.types import Tool

item_tools: list[Tool] = [
  Tool(
    name="list_items",
    description="List all items in the 1Password vault",
    inputSchema={
      "type": "object",
      "properties": {
        "vault": {
          "type": "string",
          "description": "Optional vault name to filter items",
        },
        "categories": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Optional list of categories to filter (e.g., 'Login', 'Password', 'Credit Card')",
        },
      },
    },
  ),
  Tool(
    name="get_item",
    description="Get details about a specific item by ID or name",
    inputSchema={
      "type": "object",
      "properties": {
        "item_id": {
          "type": "string",
          "description": "Item ID (UUID)",
        },
        "item_name": {
          "type": "string",
          "description": "Item name/title",
        },
        "vault": {
          "type": "string",
          "description": "Optional vault name",
        },
      },
    },
  ),
  Tool(
    name="get_password",
    description="Get the password field from an item",
    inputSchema={
      "type": "object",
      "properties": {
        "item_id": {
          "type": "string",
          "description": "Item ID (UUID)",
        },
        "item_name": {
          "type": "string",
          "description": "Item name/title",
        },
        "vault": {
          "type": "string",
          "description": "Optional vault name",
        },
      },
    },
  ),
  Tool(
    name="get_field",
    description="Get a specific field value from an item by field label",
    inputSchema={
      "type": "object",
      "properties": {
        "item_id": {
          "type": "string",
          "description": "Item ID (UUID)",
        },
        "item_name": {
          "type": "string",
          "description": "Item name/title",
        },
        "field_label": {
          "type": "string",
          "description": "Field label (e.g., 'username', 'email', 'API Key')",
        },
        "vault": {
          "type": "string",
          "description": "Optional vault name",
        },
      },
      "required": ["field_label"],
    },
  ),
  Tool(
    name="search_items",
    description="Search for items by query string (searches item titles)",
    inputSchema={
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query string",
        },
        "vault": {
          "type": "string",
          "description": "Optional vault name to search within",
        },
      },
      "required": ["query"],
    },
  ),
]
