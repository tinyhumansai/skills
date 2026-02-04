"""
Tool definitions for all calendar tools.

Each tool has a name, description, and inputSchema.
Tools are organised by domain in the tools/ subdirectory and combined into ALL_TOOLS here.
"""

from __future__ import annotations

from .tools import ALL_TOOLS

__all__ = ["ALL_TOOLS"]
