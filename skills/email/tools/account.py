"""
Account tools (6 tools).
"""

from __future__ import annotations

from mcp.types import Tool

account_tools: list[Tool] = [
  Tool(
    name="get_account_info",
    description="Get information about the connected email account",
    inputSchema={"type": "object", "properties": {}},
  ),
  Tool(
    name="get_mailbox_summary",
    description="Get all folders with message and unread counts",
    inputSchema={"type": "object", "properties": {}},
  ),
  Tool(
    name="get_unread_count",
    description="Get total unread message count across folders",
    inputSchema={
      "type": "object",
      "properties": {
        "folders": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Specific folders to check (omit for all)",
        },
      },
    },
  ),
  Tool(
    name="test_connection",
    description="Test IMAP and SMTP connectivity",
    inputSchema={"type": "object", "properties": {}},
  ),
  Tool(
    name="get_sync_status",
    description="Get current sync and polling status",
    inputSchema={"type": "object", "properties": {}},
  ),
  Tool(
    name="search_contacts",
    description="Search previously-seen email addresses",
    inputSchema={
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "Search query (matches email or name)"},
        "limit": {"type": "number", "description": "Maximum results", "default": 20},
      },
      "required": ["query"],
    },
  ),
]
