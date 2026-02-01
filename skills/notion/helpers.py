"""
Shared formatting and error handling helpers for the Notion skill.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Literal

log = logging.getLogger("skill.notion.helpers")


# ---------------------------------------------------------------------------
# Tool result
# ---------------------------------------------------------------------------


@dataclass
class ToolResult:
    content: str
    is_error: bool = False


# ---------------------------------------------------------------------------
# Rate limiter (Notion allows 3 req/s average → 350ms between calls)
# ---------------------------------------------------------------------------

_RATE_LIMIT_DELAY_MS = 350
_last_call_time: float = 0

ToolTier = Literal["read", "write"]


async def enforce_rate_limit(tier: ToolTier = "read") -> None:
    """Enforce minimum delay between Notion API calls."""
    global _last_call_time

    delay_ms = 500 if tier == "write" else _RATE_LIMIT_DELAY_MS
    now_ms = time.time() * 1000
    elapsed = now_ms - _last_call_time
    if elapsed < delay_ms:
        await asyncio.sleep((delay_ms - elapsed) / 1000)

    _last_call_time = time.time() * 1000


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def format_api_error(function_name: str, error: Exception) -> ToolResult:
    """Format a Notion API error into a user-friendly ToolResult."""
    from notion_client import APIResponseError

    if isinstance(error, APIResponseError):
        code = error.code if hasattr(error, "code") else "unknown"
        status = error.status if hasattr(error, "status") else 0

        if code == "object_not_found" or status == 404:
            msg = "Not found. Make sure the page/database is shared with your integration."
        elif code == "unauthorized" or status == 401:
            msg = "Unauthorized. Check that your integration token is valid and the page is shared with it."
        elif code == "rate_limited" or status == 429:
            msg = "Rate limited by Notion. Please try again in a moment."
        elif code == "validation_error" or status == 400:
            body = str(error)
            msg = f"Validation error: {body}"
        elif code == "restricted_resource":
            msg = "This resource is restricted. Make sure the integration has access."
        else:
            msg = f"Notion API error ({code}, HTTP {status}): {error}"

        log.error("[%s] API error: %s (code=%s, status=%s)", function_name, error, code, status)
        return ToolResult(content=msg, is_error=True)

    log.error("[%s] Unexpected error: %s", function_name, error, exc_info=True)
    return ToolResult(content=f"An error occurred in {function_name}: {error}", is_error=True)


# ---------------------------------------------------------------------------
# Formatting utilities
# ---------------------------------------------------------------------------


def extract_title(page_or_db: dict[str, Any]) -> str:
    """Extract the title string from a page or database object."""
    props = page_or_db.get("properties", {})

    # Database title property
    if "title" in page_or_db and isinstance(page_or_db["title"], list):
        return _rich_text_to_str(page_or_db["title"])

    # Page — find the title property
    for prop in props.values():
        if prop.get("type") == "title":
            return _rich_text_to_str(prop.get("title", []))

    return "Untitled"


def _rich_text_to_str(rich_text: list[dict[str, Any]]) -> str:
    """Convert Notion rich_text array to plain string."""
    return "".join(rt.get("plain_text", "") for rt in rich_text)


def format_page_summary(page: dict[str, Any]) -> str:
    """Format a page object into a concise summary string."""
    title = extract_title(page)
    page_id = page.get("id", "")
    url = page.get("url", "")
    created = page.get("created_time", "")
    edited = page.get("last_edited_time", "")
    archived = page.get("archived", False)

    lines = [f"Title: {title}", f"ID: {page_id}"]
    if url:
        lines.append(f"URL: {url}")
    if created:
        lines.append(f"Created: {created}")
    if edited:
        lines.append(f"Last edited: {edited}")
    if archived:
        lines.append("Status: Archived")
    return "\n".join(lines)


def format_database_summary(db: dict[str, Any]) -> str:
    """Format a database object into a concise summary string."""
    title = extract_title(db)
    db_id = db.get("id", "")
    url = db.get("url", "")
    desc_parts = db.get("description", [])
    description = _rich_text_to_str(desc_parts) if isinstance(desc_parts, list) else ""
    props = db.get("properties", {})

    lines = [f"Title: {title}", f"ID: {db_id}"]
    if url:
        lines.append(f"URL: {url}")
    if description:
        lines.append(f"Description: {description}")
    lines.append(f"Properties: {', '.join(props.keys())}")
    return "\n".join(lines)


def format_user_summary(user: dict[str, Any]) -> str:
    """Format a user object into a concise summary string."""
    name = user.get("name", "Unknown")
    user_id = user.get("id", "")
    user_type = user.get("type", "unknown")
    email = ""
    if user.get("person"):
        email = user["person"].get("email", "")

    lines = [f"Name: {name}", f"ID: {user_id}", f"Type: {user_type}"]
    if email:
        lines.append(f"Email: {email}")
    return "\n".join(lines)


def format_block_text(block: dict[str, Any], indent: int = 0) -> str:
    """Render a single block as text/markdown."""
    prefix = "  " * indent
    block_type = block.get("type", "")
    data = block.get(block_type, {})

    if block_type == "paragraph":
        text = _rich_text_to_str(data.get("rich_text", []))
        return f"{prefix}{text}"

    if block_type in ("heading_1", "heading_2", "heading_3"):
        level = int(block_type[-1])
        text = _rich_text_to_str(data.get("rich_text", []))
        return f"{prefix}{'#' * level} {text}"

    if block_type == "bulleted_list_item":
        text = _rich_text_to_str(data.get("rich_text", []))
        return f"{prefix}- {text}"

    if block_type == "numbered_list_item":
        text = _rich_text_to_str(data.get("rich_text", []))
        return f"{prefix}1. {text}"

    if block_type == "to_do":
        text = _rich_text_to_str(data.get("rich_text", []))
        checked = data.get("checked", False)
        marker = "[x]" if checked else "[ ]"
        return f"{prefix}{marker} {text}"

    if block_type == "toggle":
        text = _rich_text_to_str(data.get("rich_text", []))
        return f"{prefix}> {text}"

    if block_type == "code":
        text = _rich_text_to_str(data.get("rich_text", []))
        lang = data.get("language", "")
        return f"{prefix}```{lang}\n{prefix}{text}\n{prefix}```"

    if block_type == "quote":
        text = _rich_text_to_str(data.get("rich_text", []))
        return f"{prefix}> {text}"

    if block_type == "callout":
        text = _rich_text_to_str(data.get("rich_text", []))
        icon = data.get("icon", {}).get("emoji", "")
        return f"{prefix}{icon} {text}"

    if block_type == "divider":
        return f"{prefix}---"

    if block_type == "table_of_contents":
        return f"{prefix}[Table of Contents]"

    if block_type == "child_page":
        return f"{prefix}[Child Page: {data.get('title', 'Untitled')}]"

    if block_type == "child_database":
        return f"{prefix}[Child Database: {data.get('title', 'Untitled')}]"

    if block_type == "image":
        url = ""
        if data.get("type") == "external":
            url = data.get("external", {}).get("url", "")
        elif data.get("type") == "file":
            url = data.get("file", {}).get("url", "")
        caption = _rich_text_to_str(data.get("caption", []))
        return f"{prefix}![{caption}]({url})"

    if block_type == "bookmark":
        url = data.get("url", "")
        caption = _rich_text_to_str(data.get("caption", []))
        return f"{prefix}[Bookmark: {caption or url}]({url})"

    if block_type == "equation":
        expr = data.get("expression", "")
        return f"{prefix}$${expr}$$"

    # Fallback for unknown block types
    rich_text = data.get("rich_text", [])
    if rich_text:
        return f"{prefix}{_rich_text_to_str(rich_text)}"
    return f"{prefix}[{block_type} block]"


def make_rich_text(text: str) -> list[dict[str, Any]]:
    """Create a Notion rich_text array from a plain string."""
    return [{"type": "text", "text": {"content": text}}]


def results_to_json(data: Any) -> str:
    """Serialize data to a compact JSON string for tool results."""
    return json.dumps(data, indent=2, default=str)
