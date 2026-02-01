"""
Send tools (3 tools).
"""

from __future__ import annotations

from mcp.types import Tool

send_tools: list[Tool] = [
  Tool(
    name="send_email",
    description="Compose and send a new email",
    inputSchema={
      "type": "object",
      "properties": {
        "to": {
          "oneOf": [
            {
              "type": "string",
              "description": "Recipient email (or comma-separated list)",
            },
            {
              "type": "array",
              "items": {"type": "string"},
              "description": "List of recipient emails",
            },
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
        "html_body": {
          "type": "string",
          "description": "HTML body (alternative to plain text)",
        },
        "reply_to": {"type": "string", "description": "Reply-To address"},
      },
      "required": ["to", "subject", "body"],
    },
  ),
  Tool(
    name="reply_to_email",
    description="Reply to an email, preserving thread headers (In-Reply-To, References)",
    inputSchema={
      "type": "object",
      "properties": {
        "message_id": {"type": "number", "description": "UID of the message to reply to"},
        "body": {"type": "string", "description": "Reply body text"},
        "folder": {
          "type": "string",
          "description": "Folder containing the message",
          "default": "INBOX",
        },
        "reply_all": {
          "type": "boolean",
          "description": "Reply to all recipients",
          "default": False,
        },
        "html_body": {"type": "string", "description": "HTML reply body"},
      },
      "required": ["message_id", "body"],
    },
  ),
  Tool(
    name="forward_email",
    description="Forward an email to new recipients",
    inputSchema={
      "type": "object",
      "properties": {
        "message_id": {"type": "number", "description": "UID of the message to forward"},
        "to": {
          "oneOf": [
            {"type": "string"},
            {"type": "array", "items": {"type": "string"}},
          ],
          "description": "Recipient email address(es)",
        },
        "folder": {
          "type": "string",
          "description": "Folder containing the message",
          "default": "INBOX",
        },
        "body": {
          "type": "string",
          "description": "Additional message above forwarded content",
        },
        "html_body": {"type": "string", "description": "HTML body"},
      },
      "required": ["message_id", "to"],
    },
  ),
]
