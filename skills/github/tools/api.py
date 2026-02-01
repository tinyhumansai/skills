"""
Fallback / raw API tool (1 tool).
"""

from __future__ import annotations

from mcp.types import Tool

api_tools: list[Tool] = [
  Tool(
    name="gh_api",
    description="Make a raw GitHub REST API request. Use this for any endpoint not covered by the other tools",
    inputSchema={
      "type": "object",
      "properties": {
        "endpoint": {
          "type": "string",
          "description": "API endpoint path (e.g. '/repos/owner/repo/branches')",
        },
        "method": {
          "type": "string",
          "description": "HTTP method",
          "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
          "default": "GET",
        },
        "body": {
          "type": "object",
          "description": "Request body (for POST/PUT/PATCH)",
          "additionalProperties": True,
        },
      },
      "required": ["endpoint"],
    },
  ),
]
