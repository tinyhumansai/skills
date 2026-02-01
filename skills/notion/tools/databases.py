"""
Database tools (4 tools).
"""

from __future__ import annotations

from dev.types.skill_types import ToolDefinition

NOTION_QUERY_DATABASE = ToolDefinition(
  name="notion_query_database",
  description="Query a Notion database with optional filters and sorts.",
  parameters={
    "type": "object",
    "properties": {
      "database_id": {
        "type": "string",
        "description": "The database ID",
      },
      "filter": {
        "type": "object",
        "description": "Notion filter object (see Notion API docs for filter format)",
      },
      "sorts": {
        "type": "array",
        "description": 'Array of sort objects, e.g. [{"property": "Name", "direction": "ascending"}]',
        "items": {"type": "object"},
      },
      "page_size": {
        "type": "integer",
        "description": "Number of results (max 100, default 20)",
        "default": 20,
      },
    },
    "required": ["database_id"],
  },
)

NOTION_GET_DATABASE = ToolDefinition(
  name="notion_get_database",
  description="Get a Notion database's schema and metadata.",
  parameters={
    "type": "object",
    "properties": {
      "database_id": {
        "type": "string",
        "description": "The database ID",
      },
    },
    "required": ["database_id"],
  },
)

NOTION_CREATE_DATABASE = ToolDefinition(
  name="notion_create_database",
  description="Create a new database in a Notion parent page.",
  parameters={
    "type": "object",
    "properties": {
      "parent_id": {
        "type": "string",
        "description": "Parent page ID",
      },
      "title": {
        "type": "string",
        "description": "Database title",
      },
      "properties": {
        "type": "object",
        "description": "Database property schema. Keys are property names, values define type and config. A 'Name' title property is always included.",
      },
    },
    "required": ["parent_id", "title"],
  },
)

NOTION_UPDATE_DATABASE = ToolDefinition(
  name="notion_update_database",
  description="Update a Notion database's title, description, or properties.",
  parameters={
    "type": "object",
    "properties": {
      "database_id": {
        "type": "string",
        "description": "The database ID",
      },
      "title": {
        "type": "string",
        "description": "New database title",
      },
      "description": {
        "type": "string",
        "description": "New database description",
      },
      "properties": {
        "type": "object",
        "description": "Properties to add or update in the schema",
      },
    },
    "required": ["database_id"],
  },
)
