"""
Pull Request tools (16 tools).
"""

from __future__ import annotations

from mcp.types import Tool

pr_tools: list[Tool] = [
  Tool(
    name="list_prs",
    description="List pull requests in a repository with optional filters",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "limit": {
          "type": "number",
          "description": "Maximum number of pull requests to return",
          "default": 30,
        },
        "state": {
          "type": "string",
          "description": "Filter by state",
          "enum": ["open", "closed", "all"],
          "default": "open",
        },
        "base": {"type": "string", "description": "Filter by base branch name"},
        "label": {"type": "string", "description": "Filter by label name"},
      },
      "required": ["owner", "repo"],
    },
  ),
  Tool(
    name="get_pr",
    description="Get detailed information about a specific pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="create_pr",
    description="Create a new pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "title": {"type": "string", "description": "Pull request title"},
        "head": {
          "type": "string",
          "description": "The branch containing the changes (e.g. 'feature-branch' or 'user:feature-branch')",
        },
        "base": {
          "type": "string",
          "description": "The branch to merge into (defaults to repo default branch)",
        },
        "body": {"type": "string", "description": "Pull request body (Markdown supported)"},
        "draft": {
          "type": "boolean",
          "description": "Create as a draft pull request",
          "default": False,
        },
        "labels": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Labels to apply",
        },
        "assignees": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Usernames to assign",
        },
        "reviewers": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Usernames to request review from",
        },
      },
      "required": ["owner", "repo", "title", "head"],
    },
  ),
  Tool(
    name="close_pr",
    description="Close a pull request without merging",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="reopen_pr",
    description="Reopen a closed pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="merge_pr",
    description="Merge a pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
        "method": {
          "type": "string",
          "description": "Merge method to use",
          "enum": ["merge", "squash", "rebase"],
          "default": "merge",
        },
        "delete_branch": {
          "type": "boolean",
          "description": "Delete the head branch after merging",
          "default": False,
        },
        "commit_message": {"type": "string", "description": "Custom merge commit message"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="edit_pr",
    description="Edit a pull request's title, body, or base branch",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
        "title": {"type": "string", "description": "New pull request title"},
        "body": {"type": "string", "description": "New pull request body"},
        "base": {"type": "string", "description": "New base branch"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="comment_on_pr",
    description="Add a comment to a pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
        "body": {"type": "string", "description": "Comment body (Markdown supported)"},
      },
      "required": ["owner", "repo", "number", "body"],
    },
  ),
  Tool(
    name="list_pr_comments",
    description="List comments on a pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
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
    name="list_pr_reviews",
    description="List reviews on a pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="create_pr_review",
    description="Submit a review on a pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
        "event": {
          "type": "string",
          "description": "Review action to perform",
          "enum": ["APPROVE", "REQUEST_CHANGES", "COMMENT"],
        },
        "body": {"type": "string", "description": "Review comment body"},
      },
      "required": ["owner", "repo", "number", "event"],
    },
  ),
  Tool(
    name="list_pr_files",
    description="List files changed in a pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="get_pr_diff",
    description="Get the unified diff for a pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="get_pr_checks",
    description="Get CI/CD check runs and status for a pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
  Tool(
    name="request_pr_reviewers",
    description="Request reviews from specific users on a pull request",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
        "reviewers": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Usernames to request review from",
        },
      },
      "required": ["owner", "repo", "number", "reviewers"],
    },
  ),
  Tool(
    name="mark_pr_ready",
    description="Mark a draft pull request as ready for review",
    inputSchema={
      "type": "object",
      "properties": {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "number": {"type": "number", "description": "Pull request number"},
      },
      "required": ["owner", "repo", "number"],
    },
  ),
]
