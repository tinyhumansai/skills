"""
Gist tools (6 tools).
"""

from __future__ import annotations

from mcp.types import Tool

gist_tools: list[Tool] = [
  Tool(
    name="list_gists",
    description="List gists for the authenticated user or a specific user",
    inputSchema={
      "type": "object",
      "properties": {
        "limit": {
          "type": "number",
          "description": "Maximum number of gists to return",
          "default": 30,
        },
        "username": {
          "type": "string",
          "description": "GitHub username. Defaults to the authenticated user",
        },
      },
    },
  ),
  Tool(
    name="get_gist",
    description="Get a specific gist by ID, including its files and content",
    inputSchema={
      "type": "object",
      "properties": {
        "gist_id": {"type": "string", "description": "The gist ID"},
      },
      "required": ["gist_id"],
    },
  ),
  Tool(
    name="create_gist",
    description="Create a new gist with one or more files",
    inputSchema={
      "type": "object",
      "properties": {
        "files": {
          "type": "object",
          "description": 'Map of filename to file content, e.g. {"hello.py": {"content": "print(\'hello\')"}}',
          "additionalProperties": {
            "type": "object",
            "properties": {
              "content": {"type": "string", "description": "File content"},
            },
            "required": ["content"],
          },
        },
        "description": {"type": "string", "description": "Gist description"},
        "public": {
          "type": "boolean",
          "description": "Whether the gist is public",
          "default": False,
        },
      },
      "required": ["files"],
    },
  ),
  Tool(
    name="edit_gist",
    description="Edit an existing gist's description or files",
    inputSchema={
      "type": "object",
      "properties": {
        "gist_id": {"type": "string", "description": "The gist ID"},
        "description": {"type": "string", "description": "New gist description"},
        "files": {
          "type": "object",
          "description": "Map of filename to new content. Set content to null to delete a file",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "content": {"type": "string", "description": "New file content"},
            },
          },
        },
      },
      "required": ["gist_id"],
    },
  ),
  Tool(
    name="delete_gist",
    description="Permanently delete a gist",
    inputSchema={
      "type": "object",
      "properties": {
        "gist_id": {"type": "string", "description": "The gist ID to delete"},
      },
      "required": ["gist_id"],
    },
  ),
  Tool(
    name="clone_gist",
    description="Clone a gist to a local directory",
    inputSchema={
      "type": "object",
      "properties": {
        "gist_id": {"type": "string", "description": "The gist ID to clone"},
      },
      "required": ["gist_id"],
    },
  ),
]
