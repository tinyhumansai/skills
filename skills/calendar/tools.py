"""
Tool definitions for all calendar tools.

Each tool has a name, description, and inputSchema.
Tools are organised by domain in the tools/ subdirectory and combined into ALL_TOOLS here.
"""

from __future__ import annotations

from .tools.calendar import calendar_tools
from .tools.event import event_tools

ALL_TOOLS = calendar_tools + event_tools

__all__ = ["ALL_TOOLS"]
