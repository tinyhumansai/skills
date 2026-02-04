"""
Tool definitions for the browser skill.

Comprehensive browser automation tools for navigating, interacting,
and controlling web browsers via Playwright.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from mcp.types import Tool

from .tools_content import CONTENT_TOOLS
from .tools_interaction import INTERACTION_TOOLS
from .tools_navigation import NAVIGATION_TOOLS
from .tools_network import NETWORK_TOOLS
from .tools_other import OTHER_TOOLS
from .tools_storage import STORAGE_TOOLS
from .tools_wait import WAIT_TOOLS

ALL_TOOLS: list[Tool] = (
  NAVIGATION_TOOLS
  + INTERACTION_TOOLS
  + CONTENT_TOOLS
  + STORAGE_TOOLS
  + NETWORK_TOOLS
  + WAIT_TOOLS
  + OTHER_TOOLS
)
