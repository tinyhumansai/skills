"""
Flag/manage tools (7 tools).
"""

from __future__ import annotations

from mcp.types import Tool

flag_tools: list[Tool] = [
  Tool(
    name="mark_read",
    description="Mark email messages as read",
    inputSchema={
      "type": "object",
      "properties": {
        "message_ids": {
          "oneOf": [
            {"type": "number"},
            {"type": "array", "items": {"type": "number"}},
          ],
          "description": "UID(s) of messages to mark as read",
        },
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
      },
      "required": ["message_ids"],
    },
  ),
  Tool(
    name="mark_unread",
    description="Mark email messages as unread",
    inputSchema={
      "type": "object",
      "properties": {
        "message_ids": {
          "oneOf": [
            {"type": "number"},
            {"type": "array", "items": {"type": "number"}},
          ],
          "description": "UID(s) of messages to mark as unread",
        },
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
      },
      "required": ["message_ids"],
    },
  ),
  Tool(
    name="flag_message",
    description="Star/flag email messages",
    inputSchema={
      "type": "object",
      "properties": {
        "message_ids": {
          "oneOf": [
            {"type": "number"},
            {"type": "array", "items": {"type": "number"}},
          ],
          "description": "UID(s) of messages to flag",
        },
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
      },
      "required": ["message_ids"],
    },
  ),
  Tool(
    name="unflag_message",
    description="Remove star/flag from email messages",
    inputSchema={
      "type": "object",
      "properties": {
        "message_ids": {
          "oneOf": [
            {"type": "number"},
            {"type": "array", "items": {"type": "number"}},
          ],
          "description": "UID(s) of messages to unflag",
        },
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
      },
      "required": ["message_ids"],
    },
  ),
  Tool(
    name="delete_message",
    description="Move email messages to Trash",
    inputSchema={
      "type": "object",
      "properties": {
        "message_ids": {
          "oneOf": [
            {"type": "number"},
            {"type": "array", "items": {"type": "number"}},
          ],
          "description": "UID(s) of messages to delete",
        },
        "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
      },
      "required": ["message_ids"],
    },
  ),
  Tool(
    name="move_message",
    description="Move email messages to another folder",
    inputSchema={
      "type": "object",
      "properties": {
        "message_ids": {
          "oneOf": [
            {"type": "number"},
            {"type": "array", "items": {"type": "number"}},
          ],
          "description": "UID(s) of messages to move",
        },
        "destination": {"type": "string", "description": "Destination folder name"},
        "folder": {
          "type": "string",
          "description": "Source folder name",
          "default": "INBOX",
        },
      },
      "required": ["message_ids", "destination"],
    },
  ),
  Tool(
    name="archive_message",
    description="Move email messages to Archive",
    inputSchema={
      "type": "object",
      "properties": {
        "message_ids": {
          "oneOf": [
            {"type": "number"},
            {"type": "array", "items": {"type": "number"}},
          ],
          "description": "UID(s) of messages to archive",
        },
        "folder": {
          "type": "string",
          "description": "Source folder name",
          "default": "INBOX",
        },
      },
      "required": ["message_ids"],
    },
  ),
]
