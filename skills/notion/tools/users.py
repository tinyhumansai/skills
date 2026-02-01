"""
User tools (2 tools).
"""

from __future__ import annotations

from dev.types.skill_types import ToolDefinition

NOTION_LIST_USERS = ToolDefinition(
    name="notion_list_users",
    description="List all users in the Notion workspace.",
    parameters={
        "type": "object",
        "properties": {
            "page_size": {
                "type": "integer",
                "description": "Number of users to return (max 100, default 50)",
                "default": 50,
            },
        },
        "required": [],
    },
)

NOTION_GET_USER = ToolDefinition(
    name="notion_get_user",
    description="Get a Notion user by ID.",
    parameters={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "The user ID",
            },
        },
        "required": ["user_id"],
    },
)
