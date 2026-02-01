"""
Repository tools (12 tools).
"""

from __future__ import annotations

from mcp.types import Tool

repo_tools: list[Tool] = [
  Tool(
    name="list_repos",
    description="List repositories for the authenticated user or a specific owner",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {
          "type": "string",
          "description": "Repository owner (user or org). Defaults to the authenticated user",
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of repositories to return",
          "default": 30,
        },
        "visibility": {
          "type": "string",
          "description": "Filter by visibility",
          "enum": ["all", "public", "private"],
        },
        "sort": {
          "type": "string",
          "description": "Sort field",
          "enum": ["created", "updated", "pushed", "full_name"],
        },
      },
    },
  ),
  Tool(
    name="get_repo",
    description="Get detailed information about a specific repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="create_repo",
    description="Create a new repository for the authenticated user",
    inputSchema={
      "type": "object",
      "properties": {
        "name": {"type": "string", "description": "Repository name"},
        "description": {"type": "string", "description": "Repository description"},
        "visibility": {
          "type": "string",
          "description": "Repository visibility",
          "enum": ["public", "private"],
          "default": "private",
        },
        "auto_init": {
          "type": "boolean",
          "description": "Initialize with a README",
          "default": False,
        },
      },
      "required": ["name"],
    },
  ),
  Tool(
    name="fork_repo",
    description="Fork a repository to the authenticated user's account",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Owner of the repository to fork"},
        "repo": {"type": "string", "description": "Repository name to fork"},
        "fork_name": {
          "type": "string",
          "description": "Custom name for the forked repository",
        },
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="delete_repo",
    description="Permanently delete a repository. This action cannot be undone",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "confirm": {"type": "boolean", "description": "Must be true to confirm deletion"},
      },
      "required": ["owner", "repo", "confirm"],
    },
  ),
  Tool(
    name="clone_repo",
    description="Clone a repository to a local directory",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "directory": {
          "type": "string",
          "description": "Local directory path to clone into",
        },
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="list_collaborators",
    description="List collaborators on a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "limit": {
          "type": "number",
          "description": "Maximum number of collaborators to return",
          "default": 30,
        },
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="add_collaborator",
    description="Add a collaborator to a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "username": {
          "type": "string",
          "description": "GitHub username of the collaborator to add",
        },
        "permission": {
          "type": "string",
          "description": "Permission level to grant",
          "enum": ["pull", "triage", "push", "maintain", "admin"],
          "default": "push",
        },
      },
      "required": ["owner", "repo", "username"],
    },
  ),
  Tool(
    name="remove_collaborator",
    description="Remove a collaborator from a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "username": {
          "type": "string",
          "description": "GitHub username of the collaborator to remove",
        },
      },
      "required": ["owner", "repo", "username"],
    },
  ),
  Tool(
    name="list_topics",
    description="List topics (tags) on a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="set_topics",
    description="Replace all topics on a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "topics": {
          "type": "array",
          "items": {"type": "string"},
          "description": "List of topic names to set",
        },
      },
      "required": ["owner", "repo", "topics"],
    },
  ),
  Tool(
    name="list_languages",
    description="List programming languages detected in a repository",
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
