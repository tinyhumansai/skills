"""
Folder tools (5 tools).
"""

from __future__ import annotations

from mcp.types import Tool

folder_tools: list[Tool] = [
  Tool(
    name="list_folders",
    description="List all IMAP mailbox folders",
    inputSchema={
      "type": "object",
      "properties": {
        "pattern": {"type": "string", "description": "Filter folders by name pattern"},
      },
    },
  ),
  Tool(
    name="get_folder_status",
    description="Get message counts (total, unseen, recent) for a folder",
    inputSchema={
      "type": "object",
      "properties": {
        "folder": {"type": "string", "description": "Folder name (e.g. INBOX)"},
      },
      "required": ["folder"],
    },
  ),
  Tool(
    name="create_folder",
    description="Create a new IMAP folder",
    inputSchema={
      "type": "object",
      "properties": {
        "folder": {"type": "string", "description": "Name of the folder to create"},
      },
      "required": ["folder"],
    },
  ),
  Tool(
    name="rename_folder",
    description="Rename an existing IMAP folder",
    inputSchema={
      "type": "object",
      "properties": {
        "old_name": {"type": "string", "description": "Current folder name"},
        "new_name": {"type": "string", "description": "New folder name"},
      },
      "required": ["old_name", "new_name"],
    },
  ),
  Tool(
    name="delete_folder",
    description="Delete an empty IMAP folder",
    inputSchema={
      "type": "object",
      "properties": {
        "folder": {"type": "string", "description": "Name of the folder to delete"},
      },
      "required": ["folder"],
    },
  ),
]
