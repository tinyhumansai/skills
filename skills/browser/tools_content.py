"""
Content extraction tools (screenshot, get_text, get_html, etc.).
"""

from __future__ import annotations

from mcp.types import Tool

CONTENT_TOOLS: list[Tool] = [
  Tool(
    name="screenshot",
    description="Take a screenshot of the page or element",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for element to screenshot (optional, full page if omitted)",
        },
        "path": {
          "type": "string",
          "description": "File path to save screenshot (optional, returns base64 if omitted)",
        },
        "full_page": {
          "type": "boolean",
          "description": "Capture full scrollable page",
          "default": False,
        },
        "type": {
          "type": "string",
          "enum": ["png", "jpeg"],
          "description": "Image format",
          "default": "png",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_text",
    description="Get text content from an element or page",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for element (optional, gets page text if omitted)",
        },
        "inner_text": {
          "type": "boolean",
          "description": "Get innerText instead of textContent",
          "default": False,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_html",
    description="Get HTML content from an element or page",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for element (optional, gets page HTML if omitted)",
        },
        "outer_html": {
          "type": "boolean",
          "description": "Include the element itself in HTML",
          "default": True,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_attribute",
    description="Get an attribute value from an element",
    inputSchema={
      "type": "object",
      "properties": {
        "selector": {
          "type": "string",
          "description": "CSS selector for the element",
        },
        "attribute": {
          "type": "string",
          "description": "Attribute name (e.g., 'href', 'src', 'class')",
        },
      },
      "required": ["selector", "attribute"],
    },
  ),
  Tool(
    name="evaluate",
    description="Execute JavaScript in the page context and return the result",
    inputSchema={
      "type": "object",
      "properties": {
        "script": {
          "type": "string",
          "description": "JavaScript code to execute",
        },
        "arg": {
          "description": "Argument to pass to the script (will be available as 'arg' in script)",
        },
      },
      "required": ["script"],
    },
  ),
]
