"""
Storage tools (cookies, localStorage, sessionStorage).
"""

from __future__ import annotations

from mcp.types import Tool

STORAGE_TOOLS: list[Tool] = [
  Tool(
    name="get_cookies",
    description="Get all cookies for the current page",
    inputSchema={
      "type": "object",
      "properties": {
        "urls": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Optional list of URLs to get cookies for",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="set_cookie",
    description="Set a cookie",
    inputSchema={
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Cookie name",
        },
        "value": {
          "type": "string",
          "description": "Cookie value",
        },
        "url": {
          "type": "string",
          "description": "URL to set cookie for",
        },
        "domain": {
          "type": "string",
          "description": "Cookie domain",
        },
        "path": {
          "type": "string",
          "description": "Cookie path",
          "default": "/",
        },
        "expires": {
          "type": "number",
          "description": "Cookie expiration timestamp (Unix seconds)",
        },
        "http_only": {
          "type": "boolean",
          "description": "HTTP-only flag",
          "default": False,
        },
        "secure": {
          "type": "boolean",
          "description": "Secure flag (HTTPS only)",
          "default": False,
        },
        "same_site": {
          "type": "string",
          "enum": ["Strict", "Lax", "None"],
          "description": "SameSite attribute",
        },
      },
      "required": ["name", "value", "url"],
    },
  ),
  Tool(
    name="clear_cookies",
    description="Clear all cookies",
    inputSchema={
      "type": "object",
      "properties": {
        "urls": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Optional list of URLs to clear cookies for",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="get_local_storage",
    description="Get localStorage value",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "localStorage key (optional, returns all if omitted)",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="set_local_storage",
    description="Set localStorage value",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "localStorage key",
        },
        "value": {
          "type": "string",
          "description": "localStorage value",
        },
      },
      "required": ["key", "value"],
    },
  ),
  Tool(
    name="clear_local_storage",
    description="Clear all localStorage",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
  Tool(
    name="get_session_storage",
    description="Get sessionStorage value",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "sessionStorage key (optional, returns all if omitted)",
        },
      },
      "required": [],
    },
  ),
  Tool(
    name="set_session_storage",
    description="Set sessionStorage value",
    inputSchema={
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "sessionStorage key",
        },
        "value": {
          "type": "string",
          "description": "sessionStorage value",
        },
      },
      "required": ["key", "value"],
    },
  ),
  Tool(
    name="clear_session_storage",
    description="Clear all sessionStorage",
    inputSchema={
      "type": "object",
      "properties": {},
      "required": [],
    },
  ),
]
