"""
Notion tool definitions organized by domain.

Each module exports ToolDefinition objects that are combined into ALL_TOOLS.
"""

from __future__ import annotations

from dev.types.skill_types import ToolDefinition

from .pages import (
    NOTION_SEARCH,
    NOTION_GET_PAGE,
    NOTION_CREATE_PAGE,
    NOTION_UPDATE_PAGE,
    NOTION_DELETE_PAGE,
)
from .databases import (
    NOTION_QUERY_DATABASE,
    NOTION_GET_DATABASE,
    NOTION_CREATE_DATABASE,
    NOTION_UPDATE_DATABASE,
)
from .blocks import (
    NOTION_GET_BLOCK,
    NOTION_GET_BLOCK_CHILDREN,
    NOTION_APPEND_BLOCKS,
    NOTION_UPDATE_BLOCK,
    NOTION_DELETE_BLOCK,
)
from .users import (
    NOTION_LIST_USERS,
    NOTION_GET_USER,
)
from .comments import (
    NOTION_CREATE_COMMENT,
    NOTION_LIST_COMMENTS,
)
from .convenience import (
    NOTION_GET_PAGE_CONTENT,
    NOTION_APPEND_TEXT,
    NOTION_LIST_ALL_PAGES,
    NOTION_LIST_ALL_DATABASES,
)

ALL_TOOLS: list[ToolDefinition] = [
    # Pages
    NOTION_SEARCH,
    NOTION_GET_PAGE,
    NOTION_CREATE_PAGE,
    NOTION_UPDATE_PAGE,
    NOTION_DELETE_PAGE,
    # Databases
    NOTION_QUERY_DATABASE,
    NOTION_GET_DATABASE,
    NOTION_CREATE_DATABASE,
    NOTION_UPDATE_DATABASE,
    # Blocks
    NOTION_GET_BLOCK,
    NOTION_GET_BLOCK_CHILDREN,
    NOTION_APPEND_BLOCKS,
    NOTION_UPDATE_BLOCK,
    NOTION_DELETE_BLOCK,
    # Users
    NOTION_LIST_USERS,
    NOTION_GET_USER,
    # Comments
    NOTION_CREATE_COMMENT,
    NOTION_LIST_COMMENTS,
    # Convenience
    NOTION_GET_PAGE_CONTENT,
    NOTION_APPEND_TEXT,
    NOTION_LIST_ALL_PAGES,
    NOTION_LIST_ALL_DATABASES,
]
