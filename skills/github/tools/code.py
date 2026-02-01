"""
Code / File tools (3 tools).
"""

from __future__ import annotations

from mcp.types import Tool

code_tools: list[Tool] = [
  Tool(
    name="view_file",
    description="View the contents of a file in a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "path": {"type": "string", "description": "File path within the repository"},
        "ref": {
          "type": "string",
          "description": "Git ref (branch, tag, or commit SHA). Defaults to the default branch",
        },
      },
      "required": ["owner", "repo", "path"],
    },
  ),
  Tool(
    name="list_directory",
    description="List the contents of a directory in a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "path": {
          "type": "string",
          "description": "Directory path within the repository. Defaults to the root",
        },
        "ref": {
          "type": "string",
          "description": "Git ref (branch, tag, or commit SHA). Defaults to the default branch",
        },
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="get_readme",
    description="Get the README file for a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
      },
      "required": ["owner", "repo"],
    },
  ),
]
