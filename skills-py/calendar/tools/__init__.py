"""
Calendar tool definitions organized by domain.

Each module exports a list of Tool objects that are combined into ALL_TOOLS.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .calendar import calendar_tools
from .event import event_tools

if TYPE_CHECKING:
  from mcp.types import Tool

ALL_TOOLS: list[Tool] = [
  *calendar_tools,
  *event_tools,
]
