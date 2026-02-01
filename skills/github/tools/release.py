"""
Release tools (6 tools).
"""

from __future__ import annotations

from mcp.types import Tool

release_tools: list[Tool] = [
  Tool(
    name="list_releases",
    description="List releases for a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "limit": {
          "type": "number",
          "description": "Maximum number of releases to return",
          "default": 30,
        },
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="get_release",
    description="Get a specific release by tag name",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "tag": {"type": "string", "description": "Release tag name (e.g. 'v1.0.0')"},
      },
      "required": ["owner", "repo", "tag"],
    },
  ),
  Tool(
    name="create_release",
    description="Create a new release for a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "tag": {
          "type": "string",
          "description": "Tag name for the release (e.g. 'v1.0.0')",
        },
        "title": {"type": "string", "description": "Release title"},
        "notes": {
          "type": "string",
          "description": "Release notes body (Markdown supported)",
        },
        "draft": {
          "type": "boolean",
          "description": "Create as a draft release",
          "default": False,
        },
        "prerelease": {
          "type": "boolean",
          "description": "Mark as a pre-release",
          "default": False,
        },
        "target": {
          "type": "string",
          "description": "Target commitish (branch or commit SHA) for the tag",
        },
        "generate_notes": {
          "type": "boolean",
          "description": "Auto-generate release notes from commits",
          "default": False,
        },
      },
      "required": ["owner", "repo", "tag"],
    },
  ),
  Tool(
    name="delete_release",
    description="Delete a release by tag name",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "tag": {"type": "string", "description": "Release tag name to delete"},
        "cleanup_tag": {
          "type": "boolean",
          "description": "Also delete the associated git tag",
          "default": False,
        },
      },
      "required": ["owner", "repo", "tag"],
    },
  ),
  Tool(
    name="list_release_assets",
    description="List assets (downloadable files) attached to a release",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "tag": {"type": "string", "description": "Release tag name"},
      },
      "required": ["owner", "repo", "tag"],
    },
  ),
  Tool(
    name="get_latest_release",
    description="Get the latest published release for a repository",
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
