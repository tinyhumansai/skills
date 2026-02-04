"""
Tool definitions for all 1Password tools.

Each tool has a name, description, and inputSchema.
Tools are organised by domain in the tools/ subdirectory and combined into ALL_TOOLS here.
"""

from __future__ import annotations

from .item import item_tools

ALL_TOOLS = item_tools

__all__ = ["ALL_TOOLS"]
