"""
Email tool definitions organized by domain.

Each module exports a list of Tool objects that are combined into ALL_TOOLS.
"""

from __future__ import annotations

from mcp.types import Tool

from .folder import folder_tools
from .message import message_tools
from .send import send_tools
from .flag import flag_tools
from .attachment import attachment_tools
from .draft import draft_tools
from .account import account_tools

ALL_TOOLS: list[Tool] = [
    *folder_tools,
    *message_tools,
    *send_tools,
    *flag_tools,
    *attachment_tools,
    *draft_tools,
    *account_tools,
]
