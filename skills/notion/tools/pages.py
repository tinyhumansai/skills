"""
Page tools (5 tools).
"""

from __future__ import annotations

from dev.types.skill_types import ToolDefinition

NOTION_SEARCH = ToolDefinition(
    name="notion_search",
    description="Search pages and databases in the connected Notion workspace.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text",
            },
            "filter": {
                "type": "string",
                "enum": ["page", "database"],
                "description": "Filter results by object type (page or database). Omit to search both.",
            },
            "page_size": {
                "type": "integer",
                "description": "Number of results to return (max 100, default 20)",
                "default": 20,
            },
        },
        "required": [],
    },
)

NOTION_GET_PAGE = ToolDefinition(
    name="notion_get_page",
    description="Get a Notion page's properties by ID.",
    parameters={
        "type": "object",
        "properties": {
            "page_id": {
                "type": "string",
                "description": "The page ID (UUID format, with or without dashes)",
            },
        },
        "required": ["page_id"],
    },
)

NOTION_CREATE_PAGE = ToolDefinition(
    name="notion_create_page",
    description="Create a new page in a Notion parent (page or database).",
    parameters={
        "type": "object",
        "properties": {
            "parent_id": {
                "type": "string",
                "description": "Parent page or database ID",
            },
            "parent_type": {
                "type": "string",
                "enum": ["page", "database"],
                "description": "Whether the parent is a page or database (default: page)",
                "default": "page",
            },
            "title": {
                "type": "string",
                "description": "Page title",
            },
            "content": {
                "type": "string",
                "description": "Optional text content to add as a paragraph block",
            },
            "properties": {
                "type": "object",
                "description": "Additional page properties (for database entries). Keys are property names, values follow Notion property value format.",
            },
        },
        "required": ["parent_id", "title"],
    },
)

NOTION_UPDATE_PAGE = ToolDefinition(
    name="notion_update_page",
    description="Update a Notion page's properties or archive status.",
    parameters={
        "type": "object",
        "properties": {
            "page_id": {
                "type": "string",
                "description": "The page ID",
            },
            "title": {
                "type": "string",
                "description": "New title for the page",
            },
            "properties": {
                "type": "object",
                "description": "Properties to update. Keys are property names, values follow Notion property value format.",
            },
            "archived": {
                "type": "boolean",
                "description": "Set to true to archive, false to unarchive",
            },
        },
        "required": ["page_id"],
    },
)

NOTION_DELETE_PAGE = ToolDefinition(
    name="notion_delete_page",
    description="Archive (soft-delete) a Notion page.",
    parameters={
        "type": "object",
        "properties": {
            "page_id": {
                "type": "string",
                "description": "The page ID to archive",
            },
        },
        "required": ["page_id"],
    },
)
