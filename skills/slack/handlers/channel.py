"""Channel-related tool handlers."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..client.slack_client import get_client
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import ValidationError, validate_channel_id

log = logging.getLogger("skill.slack.handlers.channel")


async def list_channels(args: dict[str, Any]) -> ToolResult:
    """List Slack channels."""
    try:
        include_private = args.get("include_private", False)
        include_archived = not args.get("include_archived", False)  # Slack uses exclude_archived
        limit = args.get("limit", 50)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        types = "public_channel"
        if include_private:
            types += ",private_channel"

        result = await client.conversations_list(
            types=types,
            exclude_archived=include_archived,
            limit=min(limit, 200),
        )

        channels = result.get("channels", [])
        channel_list = []
        for ch in channels[:limit]:
            channel_list.append(
                {
                    "id": ch.get("id"),
                    "name": ch.get("name"),
                    "is_private": ch.get("is_private", False),
                    "is_archived": ch.get("is_archived", False),
                    "topic": ch.get("topic", {}).get("value", ""),
                    "purpose": ch.get("purpose", {}).get("value", ""),
                    "member_count": ch.get("num_members", 0),
                }
            )

        return ToolResult(content=json.dumps({"channels": channel_list}, indent=2))

    except Exception as e:
        return log_and_format_error("list_channels", e, ErrorCategory.CHANNEL)


async def get_channel(args: dict[str, Any]) -> ToolResult:
    """Get channel information."""
    try:
        channel_id = args.get("channel_id", "")
        validate_channel_id(channel_id)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        result = await client.conversations_info(channel_id)
        channel = result.get("channel", {})

        info = {
            "id": channel.get("id"),
            "name": channel.get("name"),
            "is_private": channel.get("is_private", False),
            "is_archived": channel.get("is_archived", False),
            "topic": channel.get("topic", {}).get("value", ""),
            "purpose": channel.get("purpose", {}).get("value", ""),
            "member_count": channel.get("num_members", 0),
            "created": channel.get("created"),
        }

        return ToolResult(content=json.dumps(info, indent=2))

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("get_channel", e, ErrorCategory.CHANNEL)


async def create_channel(args: dict[str, Any]) -> ToolResult:
    """Create a channel."""
    try:
        name = args.get("name", "").strip()
        if not name:
            raise ValidationError("name is required")
        is_private = args.get("is_private", False)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        result = await client.conversations_create(name, is_private)
        channel = result.get("channel", {})

        return ToolResult(
            content=json.dumps(
                {
                    "id": channel.get("id"),
                    "name": channel.get("name"),
                    "is_private": channel.get("is_private", False),
                },
                indent=2,
            )
        )

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("create_channel", e, ErrorCategory.CHANNEL)


async def join_channel(args: dict[str, Any]) -> ToolResult:
    """Join a channel."""
    try:
        channel_id = args.get("channel_id", "")
        validate_channel_id(channel_id)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        await client.conversations_join(channel_id)
        return ToolResult(content=f"Successfully joined channel {channel_id}")

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("join_channel", e, ErrorCategory.CHANNEL)


async def leave_channel(args: dict[str, Any]) -> ToolResult:
    """Leave a channel."""
    try:
        channel_id = args.get("channel_id", "")
        validate_channel_id(channel_id)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        await client.conversations_leave(channel_id)
        return ToolResult(content=f"Successfully left channel {channel_id}")

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("leave_channel", e, ErrorCategory.CHANNEL)


async def archive_channel(args: dict[str, Any]) -> ToolResult:
    """Archive a channel."""
    try:
        channel_id = args.get("channel_id", "")
        validate_channel_id(channel_id)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        await client.conversations_archive(channel_id)
        return ToolResult(content=f"Successfully archived channel {channel_id}")

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("archive_channel", e, ErrorCategory.CHANNEL)


async def unarchive_channel(args: dict[str, Any]) -> ToolResult:
    """Unarchive a channel."""
    try:
        channel_id = args.get("channel_id", "")
        validate_channel_id(channel_id)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        await client.conversations_unarchive(channel_id)
        return ToolResult(content=f"Successfully unarchived channel {channel_id}")

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("unarchive_channel", e, ErrorCategory.CHANNEL)


async def set_channel_topic(args: dict[str, Any]) -> ToolResult:
    """Set channel topic."""
    try:
        channel_id = args.get("channel_id", "")
        topic = args.get("topic", "").strip()
        validate_channel_id(channel_id)
        if not topic:
            raise ValidationError("topic is required")

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        await client.conversations_set_topic(channel_id, topic)
        return ToolResult(content=f"Successfully set topic for channel {channel_id}")

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("set_channel_topic", e, ErrorCategory.CHANNEL)


async def set_channel_purpose(args: dict[str, Any]) -> ToolResult:
    """Set channel purpose."""
    try:
        channel_id = args.get("channel_id", "")
        purpose = args.get("purpose", "").strip()
        validate_channel_id(channel_id)
        if not purpose:
            raise ValidationError("purpose is required")

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        await client.conversations_set_purpose(channel_id, purpose)
        return ToolResult(content=f"Successfully set purpose for channel {channel_id}")

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("set_channel_purpose", e, ErrorCategory.CHANNEL)


async def get_channel_members(args: dict[str, Any]) -> ToolResult:
    """Get channel members."""
    try:
        channel_id = args.get("channel_id", "")
        limit = args.get("limit", 100)
        validate_channel_id(channel_id)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        result = await client.conversations_members(channel_id, limit=min(limit, 200))
        members = result.get("members", [])

        return ToolResult(content=json.dumps({"members": members, "count": len(members)}, indent=2))

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("get_channel_members", e, ErrorCategory.CHANNEL)
