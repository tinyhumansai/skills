"""
Comment tools (2 tools).
"""

from __future__ import annotations

from dev.types.skill_types import ToolDefinition

NOTION_CREATE_COMMENT = ToolDefinition(
    name="notion_create_comment",
    description="Create a comment on a Notion page.",
    parameters={
        "type": "object",
        "properties": {
            "parent_id": {
                "type": "string",
                "description": "The page ID to comment on",
            },
            "text": {
                "type": "string",
                "description": "Comment text",
            },
        },
        "required": ["parent_id", "text"],
    },
)

NOTION_LIST_COMMENTS = ToolDefinition(
    name="notion_list_comments",
    description="List comments on a Notion page or block.",
    parameters={
        "type": "object",
        "properties": {
            "block_id": {
                "type": "string",
                "description": "The page or block ID",
            },
            "page_size": {
                "type": "integer",
                "description": "Number of comments to return (max 100, default 20)",
                "default": 20,
            },
        },
        "required": ["block_id"],
    },
)
