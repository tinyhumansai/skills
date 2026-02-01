"""
Issue tools (12 tools).
"""

from __future__ import annotations

from mcp.types import Tool

issue_tools: list[Tool] = [
  Tool(
    name="list_issues",
    description="List issues in a repository with optional filters",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "limit": {
          "type": "number",
          "description": "Maximum number of issues to return",
          "default": 30,
        },
        "state": {
          "type": "string",
          "description": "Filter by state",
          "enum": ["open", "closed", "all"],
          "default": "open",
        },
        "label": {"type": "string", "description": "Filter by label name"},
        "assignee": {"type": "string", "description": "Filter by assignee username"},
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="get_issue",
    description="Get detailed information about a specific issue",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Issue number"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="create_issue",
    description="Create a new issue in a repository",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "title": {"type": "string", "description": "Issue title"},
        "body": {"type": "string", "description": "Issue body (Markdown supported)"},
        "labels": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Labels to apply to the issue",
        },
        "assignees": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Usernames to assign to the issue",
        },
      },
      "required": ["owner", "repo", "title"],
    },
  ),
  Tool(
    name="close_issue",
    description="Close an issue",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Issue number"},
        "reason": {
          "type": "string",
          "description": "Reason for closing",
          "enum": ["completed", "not_planned"],
        },
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="reopen_issue",
    description="Reopen a closed issue",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Issue number"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="edit_issue",
    description="Edit an existing issue's title or body",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Issue number"},
        "title": {"type": "string", "description": "New issue title"},
        "body": {"type": "string", "description": "New issue body"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="comment_on_issue",
    description="Add a comment to an issue",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Issue number"},
        "body": {"type": "string", "description": "Comment body (Markdown supported)"},
      },
      "required": ["owner", "repo", "number", "body"],
    },
  ),
  Tool(
    name="list_issue_comments",
    description="List comments on an issue",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Issue number"},
        "limit": {
          "type": "number",
          "description": "Maximum number of comments to return",
          "default": 30,
        },
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="add_issue_labels",
    description="Add labels to an issue",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Issue number"},
        "labels": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Labels to add",
        },
      },
      "required": ["owner", "repo", "number", "labels"],
    },
  ),
  Tool(
    name="remove_issue_labels",
    description="Remove labels from an issue",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Issue number"},
        "labels": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Labels to remove",
        },
      },
      "required": ["owner", "repo", "number", "labels"],
    },
  ),
  Tool(
    name="add_issue_assignees",
    description="Add assignees to an issue",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Issue number"},
        "assignees": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Usernames to assign",
        },
      },
      "required": ["owner", "repo", "number", "assignees"],
    },
  ),
  Tool(
    name="remove_issue_assignees",
    description="Remove assignees from an issue",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Issue number"},
        "assignees": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Usernames to remove",
        },
      },
      "required": ["owner", "repo", "number", "assignees"],
    },
  ),
]
