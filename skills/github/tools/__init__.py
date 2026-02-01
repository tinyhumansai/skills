"""
GitHub tool definitions organized by domain.

Each module exports a list of Tool objects that are combined into ALL_TOOLS.
"""

from __future__ import annotations

from mcp.types import Tool

from .repo import repo_tools
from .issue import issue_tools
from .pr import pr_tools
from .search import search_tools
from .code import code_tools
from .release import release_tools
from .gist import gist_tools
from .actions import actions_tools
from .notification import notification_tools
from .api import api_tools

ALL_TOOLS: list[Tool] = [
    *repo_tools,
    *issue_tools,
    *pr_tools,
    *search_tools,
    *code_tools,
    *release_tools,
    *gist_tools,
    *actions_tools,
    *notification_tools,
    *api_tools,
]
