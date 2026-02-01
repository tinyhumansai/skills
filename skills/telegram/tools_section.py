from __future__ import annotations
from mcp.types import Tool

"""Section: ---------------------------------------------------------------------------"""

# ---------------------------------------------------------------------------

ALL_TOOLS: list[Tool] = [
  *chat_tools,
  *message_tools,
  *contact_tools,
  *admin_tools,
  *profile_media_tools,
  *settings_tools,
  *search_tools,
]
