"""
Notification tools (3 tools).
"""

from __future__ import annotations

from mcp.types import Tool

notification_tools: list[Tool] = [
  Tool(
    name="list_notifications",
    description="List GitHub notifications for the authenticated user",
    inputSchema={
      "type": "object",
      "properties": {
        "all": {
          "type": "boolean",
          "description": "Include read notifications",
          "default": False,
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of notifications to return",
          "default": 50,
        },
      },
    },
  ),
  Tool(
    name="mark_notification_read",
    description="Mark a specific notification thread as read",
    inputSchema={
      "type": "object",
      "properties": {
        "thread_id": {"type": "string", "description": "Notification thread ID"},
      },
      "required": ["thread_id"],
    },
  ),
  Tool(
    name="mark_all_notifications_read",
    description="Mark all notifications as read",
    inputSchema={
      "type": "object",
      "properties": {},
    },
  ),
]
