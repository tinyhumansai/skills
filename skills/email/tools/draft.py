"""
Draft tools (4 tools).
"""

from __future__ import annotations

from mcp.types import Tool

draft_tools: list[Tool] = [
  Tool(
    name="save_draft",
    description="Save a draft email to the Drafts folder",
    inputSchema={
      "type": "object",
      "properties": {
        "to": {
          "oneOf": [
            {"type": "string"},
            {"type": "array", "items": {"type": "string"}},
          ],
          "description": "Recipient email address(es)",
        },
        "subject": {"type": "string", "description": "Email subject"},
        "body": {"type": "string", "description": "Plain text body"},
        "cc": {
          "type": "array",
          "items": {"type": "string"},
          "description": "CC recipients",
        },
        "bcc": {
          "type": "array",
          "items": {"type": "string"},
          "description": "BCC recipients",
        },
        "html_body": {"type": "string", "description": "HTML body"},
      },
      "required": ["to", "subject", "body"],
    },
  ),
  Tool(
    name="list_drafts",
    description="List draft email messages",
    inputSchema={
      "type": "object",
      "properties": {
        "limit": {
          "type": "number",
          "description": "Maximum drafts to return",
          "default": 20,
        },
      },
    },
  ),
  Tool(
    name="update_draft",
    description="Update an existing draft email",
    inputSchema={
      "type": "object",
      "properties": {
        "message_id": {"type": "number", "description": "UID of the draft to update"},
        "to": {
          "oneOf": [
            {"type": "string"},
            {"type": "array", "items": {"type": "string"}},
          ],
          "description": "New recipient(s)",
        },
        "subject": {"type": "string", "description": "New subject"},
        "body": {"type": "string", "description": "New body text"},
        "html_body": {"type": "string", "description": "New HTML body"},
      },
      "required": ["message_id"],
    },
  ),
  Tool(
    name="delete_draft",
    description="Delete a draft email",
    inputSchema={
      "type": "object",
      "properties": {
        "message_id": {"type": "number", "description": "UID of the draft to delete"},
      },
      "required": ["message_id"],
    },
  ),
]
