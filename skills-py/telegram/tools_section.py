"""Telegram tool definitions — consolidated list of all MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from mcp.types import Tool

# Tool lists (to be populated from individual tool modules)
# For now, using empty lists to fix import errors
# TODO: Import actual tool definitions from tool modules
chat_tools: list[Tool] = []
message_tools: list[Tool] = []
contact_tools: list[Tool] = []
admin_tools: list[Tool] = []
profile_media_tools: list[Tool] = []
settings_tools: list[Tool] = []
search_tools: list[Tool] = []

ALL_TOOLS: list[Tool] = [
  *chat_tools,
  *message_tools,
  *contact_tools,
  *admin_tools,
  *profile_media_tools,
  *settings_tools,
  *search_tools,
]
