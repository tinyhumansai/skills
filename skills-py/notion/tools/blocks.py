"""
Block tools (5 tools).
"""

from __future__ import annotations

from dev.types.skill_types import ToolDefinition

NOTION_GET_BLOCK = ToolDefinition(
  name="notion_get_block",
  description="Get a single Notion block by ID.",
  parameters={
    "type": "object",
    "properties": {
      "block_id": {
        "type": "string",
        "description": "The block ID",
      },
    },
    "required": ["block_id"],
  },
)

NOTION_GET_BLOCK_CHILDREN = ToolDefinition(
  name="notion_get_block_children",
  description="List child blocks of a Notion block or page.",
  parameters={
    "type": "object",
    "properties": {
      "block_id": {
        "type": "string",
        "description": "The parent block or page ID",
      },
      "page_size": {
        "type": "integer",
        "description": "Number of blocks to return (max 100, default 50)",
        "default": 50,
      },
    },
    "required": ["block_id"],
  },
)

NOTION_APPEND_BLOCKS = ToolDefinition(
  name="notion_append_blocks",
  description="Append child blocks to a Notion page or block.",
  parameters={
    "type": "object",
    "properties": {
      "block_id": {
        "type": "string",
        "description": "The parent block or page ID",
      },
      "children": {
        "type": "array",
        "description": "Array of block objects to append (Notion block format)",
        "items": {"type": "object"},
      },
    },
    "required": ["block_id", "children"],
  },
)

NOTION_UPDATE_BLOCK = ToolDefinition(
  name="notion_update_block",
  description="Update a Notion block's content.",
  parameters={
    "type": "object",
    "properties": {
      "block_id": {
        "type": "string",
        "description": "The block ID",
      },
      "content": {
        "type": "object",
        "description": "Block content update object. The key should be the block type (e.g. 'paragraph') with the updated content.",
      },
    },
    "required": ["block_id", "content"],
  },
)

NOTION_DELETE_BLOCK = ToolDefinition(
  name="notion_delete_block",
  description="Delete a Notion block.",
  parameters={
    "type": "object",
    "properties": {
      "block_id": {
        "type": "string",
        "description": "The block ID to delete",
      },
    },
    "required": ["block_id"],
  },
)
