"""
Calendar management tools (2 tools).
"""

from __future__ import annotations

from mcp.types import Tool

calendar_tools: list[Tool] = [
  Tool(
    name="list_calendars",
    description="List all calendars in the connected account",
    inputSchema={
      "type": "object",
      "properties": {
        "show_hidden": {
          "type": "boolean",
          "description": "Include hidden calendars",
          "default": False,
        },
      },
    },
  ),
  Tool(
    name="get_calendar",
    description="Get details about a specific calendar",
    inputSchema={
      "type": "object",
      "properties": {
        "calendar_id": {
          "type": "string",
          "description": "Calendar ID (use 'primary' for primary calendar)",
        },
      },
      "required": ["calendar_id"],
    },
  ),
]
