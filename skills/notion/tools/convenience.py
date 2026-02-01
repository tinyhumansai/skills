"""
Convenience tools (4 tools).
"""

from __future__ import annotations

from dev.types.skill_types import ToolDefinition

NOTION_GET_PAGE_CONTENT = ToolDefinition(
    name="notion_get_page_content",
    description="Recursively fetch and render all blocks of a Notion page as readable text/markdown.",
    parameters={
        "type": "object",
        "properties": {
            "page_id": {
                "type": "string",
                "description": "The page ID",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum nesting depth to fetch (default 3)",
                "default": 3,
            },
        },
        "required": ["page_id"],
    },
)

NOTION_APPEND_TEXT = ToolDefinition(
    name="notion_append_text",
    description="Append a text block to a Notion page (convenience wrapper for append_blocks).",
    parameters={
        "type": "object",
        "properties": {
            "page_id": {
                "type": "string",
                "description": "The page ID",
            },
            "text": {
                "type": "string",
                "description": "Text to append",
            },
            "type": {
                "type": "string",
                "enum": [
                    "paragraph",
                    "heading_1",
                    "heading_2",
                    "heading_3",
                    "bulleted_list_item",
                    "numbered_list_item",
                    "to_do",
                ],
                "description": "Block type (default: paragraph)",
                "default": "paragraph",
            },
        },
        "required": ["page_id", "text"],
    },
)

NOTION_LIST_ALL_PAGES = ToolDefinition(
    name="notion_list_all_pages",
    description="List all pages accessible to the integration.",
    parameters={
        "type": "object",
        "properties": {
            "page_size": {
                "type": "integer",
                "description": "Number of pages to return (max 100, default 20)",
                "default": 20,
            },
        },
        "required": [],
    },
)

NOTION_LIST_ALL_DATABASES = ToolDefinition(
    name="notion_list_all_databases",
    description="List all databases accessible to the integration.",
    parameters={
        "type": "object",
        "properties": {
            "page_size": {
                "type": "integer",
                "description": "Number of databases to return (max 100, default 20)",
                "default": 20,
            },
        },
        "required": [],
    },
)
