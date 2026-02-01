"""
Message read tools (7 tools).
"""

from __future__ import annotations

from mcp.types import Tool

message_tools: list[Tool] = [
  Tool(
    name="list_messages",
    description="List email message summaries in a folder",
    inputSchema={
      "type": "object",
      "properties": {
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
        "limit": {
          "type": "number",
          "description": "Maximum messages to return",
          "default": 20,
        },
        "offset": {"type": "number", "description": "Offset for pagination", "default": 0},
        "sort": {
          "type": "string",
          "description": "Sort order: date_desc or date_asc",
          "default": "date_desc",
        },
      },
    },
  ),
  Tool(
    name="get_message",
    description="Get full email message content including body",
    inputSchema={
      "type": "object",
      "properties": {
        "message_id": {"type": "number", "description": "The UID of the message"},
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
        "format": {
          "type": "string",
          "description": "Body format: text, html, or raw",
          "default": "text",
        },
      },
      "required": ["message_id"],
    },
  ),
  Tool(
    name="search_messages",
    description="Search emails by content, sender, subject, date, or other criteria",
    inputSchema={
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "Text search query"},
        "folder": {"type": "string", "description": "Folder to search in (omit for INBOX)"},
        "limit": {"type": "number", "description": "Maximum results", "default": 20},
        "from_addr": {"type": "string", "description": "Filter by sender email address"},
        "to_addr": {"type": "string", "description": "Filter by recipient email address"},
        "subject": {"type": "string", "description": "Filter by subject text"},
        "since": {
          "type": "string",
          "description": "Messages after this date (DD-Mon-YYYY)",
        },
        "before": {
          "type": "string",
          "description": "Messages before this date (DD-Mon-YYYY)",
        },
        "has_attachment": {
          "type": "boolean",
          "description": "Filter for messages with attachments",
        },
      },
    },
  ),
  Tool(
    name="get_unread_messages",
    description="Get unread messages in a folder",
    inputSchema={
      "type": "object",
      "properties": {
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
        "limit": {"type": "number", "description": "Maximum messages", "default": 20},
      },
    },
  ),
  Tool(
    name="get_thread",
    description="Get all messages in an email thread",
    inputSchema={
      "type": "object",
      "properties": {
        "message_id": {"type": "number", "description": "UID of any message in the thread"},
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
      },
      "required": ["message_id"],
    },
  ),
  Tool(
    name="count_messages",
    description="Get the message count for a folder",
    inputSchema={
      "type": "object",
      "properties": {
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
      },
    },
  ),
  Tool(
    name="get_recent_messages",
    description="Get messages received in the last N hours",
    inputSchema={
      "type": "object",
      "properties": {
        "hours": {
          "type": "number",
          "description": "Number of hours to look back",
          "default": 24,
        },
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
        "limit": {"type": "number", "description": "Maximum messages", "default": 20},
      },
    },
  ),
]
