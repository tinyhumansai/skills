"""
Search tools (4 tools).
"""

from __future__ import annotations

from mcp.types import Tool

search_tools: list[Tool] = [
  Tool(
    name="search_repos",
    description="Search GitHub repositories by query",
    inputSchema={
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query (supports GitHub search syntax)",
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of results to return",
          "default": 30,
        },
        "sort": {
          "type": "string",
          "description": "Sort field",
          "enum": ["stars", "forks", "help-wanted-issues", "updated"],
        },
        "order": {
          "type": "string",
          "description": "Sort order",
          "enum": ["asc", "desc"],
          "default": "desc",
        },
      },
      "required": ["query"],
    },
  ),
  Tool(
    name="search_issues",
    description="Search issues and pull requests across GitHub",
    inputSchema={
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query (supports GitHub search syntax, e.g. 'is:issue is:open label:bug')",
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of results to return",
          "default": 30,
        },
        "sort": {
          "type": "string",
          "description": "Sort field",
          "enum": ["comments", "reactions", "created", "updated"],
        },
      },
      "required": ["query"],
    },
  ),
  Tool(
    name="search_code",
    description="Search code across GitHub repositories",
    inputSchema={
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query (supports GitHub code search syntax)",
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of results to return",
          "default": 30,
        },
        "repo": {
          "type": "string",
          "description": "Restrict search to a specific repo (owner/name format)",
        },
        "language": {"type": "string", "description": "Filter by programming language"},
      },
      "required": ["query"],
    },
  ),
  Tool(
    name="search_commits",
    description="Search commits across GitHub repositories",
    inputSchema={
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query (supports GitHub commit search syntax)",
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of results to return",
          "default": 30,
        },
        "repo": {
          "type": "string",
          "description": "Restrict search to a specific repo (owner/name format)",
        },
      },
      "required": ["query"],
    },
  ),
]
