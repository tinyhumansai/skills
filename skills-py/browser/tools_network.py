"""
Network tools (request interception, network logs).
"""

from __future__ import annotations

from mcp.types import Tool

NETWORK_TOOLS: list[Tool] = [
  Tool(
    name="intercept_request",
    description="Intercept and modify network requests",
    inputSchema={
      "type": "object",
      "properties": {
        "url_pattern": {
          "type": "string",
          "description": "URL pattern to intercept (supports glob or regex)",
        },
        "action": {
          "type": "string",
          "enum": ["abort", "continue", "fulfill", "respond"],
          "description": "Action to take: abort, continue, fulfill with custom response, or respond with custom data",
          "default": "continue",
        },
        "response_status": {
          "type": "number",
          "description": "HTTP status code for fulfill/respond action",
          "default": 200,
        },
        "response_body": {
          "type": "string",
          "description": "Response body for fulfill/respond action",
        },
        "response_headers": {
          "type": "object",
          "description": "Custom response headers",
        },
      },
      "required": ["url_pattern"],
    },
  ),
  Tool(
    name="get_network_logs",
    description="Get network request/response logs",
    inputSchema={
      "type": "object",
      "properties": {
        "url_pattern": {
          "type": "string",
          "description": "Filter logs by URL pattern (optional)",
        },
        "method": {
          "type": "string",
          "description": "Filter by HTTP method (optional)",
        },
        "status": {
          "type": "number",
          "description": "Filter by status code (optional)",
        },
      },
      "required": [],
    },
  ),
]
