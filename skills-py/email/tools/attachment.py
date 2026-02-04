"""
Attachment tools (3 tools).
"""

from __future__ import annotations

from mcp.types import Tool

attachment_tools: list[Tool] = [
  Tool(
    name="list_attachments",
    description="List attachments on an email message",
    inputSchema={
      "type": "object",
      "properties": {
        "message_id": {"type": "number", "description": "UID of the message"},
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
      },
      "required": ["message_id"],
    },
  ),
  Tool(
    name="get_attachment_info",
    description="Get metadata for a specific attachment",
    inputSchema={
      "type": "object",
      "properties": {
        "message_id": {"type": "number", "description": "UID of the message"},
        "attachment_index": {
          "type": "number",
          "description": "Index of the attachment (0-based)",
        },
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
      },
      "required": ["message_id", "attachment_index"],
    },
  ),
  Tool(
    name="save_attachment",
    description="Save an attachment to the skill's data directory",
    inputSchema={
      "type": "object",
      "properties": {
        "message_id": {"type": "number", "description": "UID of the message"},
        "attachment_index": {
          "type": "number",
          "description": "Index of the attachment (0-based)",
        },
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
        "filename": {"type": "string", "description": "Override filename for saving"},
      },
      "required": ["message_id", "attachment_index"],
    },
  ),
]
