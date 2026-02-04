"""
Wait tools (waiting for selectors, URLs, etc.).
"""

from __future__ import annotations

from mcp.types import Tool

WAIT_TOOLS: list[Tool] = [
  Tool(
    name="wait_for_selector",
    description="Wait for an element to appear on the page",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector to wait for",
        },
        "state": {
          "type": "string",
          "enum": ["attached", "detached", "visible", "hidden"],
          "description": "Element state to wait for",
          "default": "visible",
        },
        "timeout": {
          "type": "number",
          "description": "Timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": ["selector"],
    },
  ),
  Tool(
    name="wait_for_url",
    description="Wait for the page URL to match a pattern",
    inputSchema={
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "URL pattern (supports glob or regex)",
        },
        "timeout": {
          "type": "number",
          "description": "Timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": ["url"],
    },
  ),
]
