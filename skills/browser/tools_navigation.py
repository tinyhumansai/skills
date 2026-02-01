"""
Navigation and page management tools.
"""

from __future__ import annotations

from mcp.types import Tool

NAVIGATION_TOOLS: list[Tool] = [
  Tool(
    name="navigate",
    description="Navigate to a URL in the browser",
    inputSchema={
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "URL to navigate to",
        },
        "wait_until": {
          "type": "string",
          "enum": ["load", "domcontentloaded", "networkidle", "commit"],
          "description": "When to consider navigation successful",
          "default": "load",
        },
        "timeout": {
          "type": "number",
          "description": "Navigation timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": ["url"],
    },
  ),
  Tool(
    name="go_back",
    description="Navigate back in browser history",
    inputSchema={
      "type": "object",
      "properties": {
        "timeout": {
          "type": "number",
          "description": "Navigation timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="go_forward",
    description="Navigate forward in browser history",
    inputSchema={
      "type": "object",
      "properties": {
        "timeout": {
          "type": "number",
          "description": "Navigation timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="reload",
    description="Reload the current page",
    inputSchema={
      "type": "object",
      "properties": {
        "wait_until": {
          "type": "string",
          "enum": ["load", "domcontentloaded", "networkidle", "commit"],
          "description": "When to consider reload successful",
          "default": "load",
        },
        "timeout": {
          "type": "number",
          "description": "Navigation timeout in milliseconds",
          "default": 30000,
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_url",
    description="Get the current page URL",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="get_title",
    description="Get the current page title",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="close_page",
    description="Close the current page",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="new_page",
    description="Open a new page/tab",
    inputSchema={
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "URL to navigate to in the new page (optional)",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_pages",
    description="Get list of all open pages/tabs",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="switch_page",
    description="Switch to a different page/tab",
    inputSchema={
      "type": "object",
      "properties": {
        "index": {
          "type": "number",
          "description": "Page index (0-based)",
        },
        "url": {
          "type": "string",
          "description": "Page URL to switch to (alternative to index)",
        },
      },
      "required": [],
    },
  ),
]
