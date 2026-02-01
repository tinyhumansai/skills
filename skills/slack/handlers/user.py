"""User-related tool handlers."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..client.slack_client import get_client
from ..helpers import ErrorCategory, ToolResult, log_and_format_error
from ..validation import ValidationError, validate_user_id

log = logging.getLogger("skill.slack.handlers.user")


async def list_users(args: dict[str, Any]) -> ToolResult:
    """List users."""
    try:
        limit = args.get("limit", 100)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        result = await client.users_list(limit=min(limit, 200))
        users = result.get("members", [])

        user_list = []
        for user in users[:limit]:
            if user.get("deleted") or user.get("is_restricted"):
                continue
            user_list.append(
                {
                    "id": user.get("id"),
                    "name": user.get("name"),
                    "real_name": user.get("real_name", ""),
                    "email": user.get("profile", {}).get("email", ""),
                    "is_bot": user.get("is_bot", False),
                    "is_admin": user.get("is_admin", False),
                }
            )

        return ToolResult(content=json.dumps({"users": user_list}, indent=2))

    except Exception as e:
        return log_and_format_error("list_users", e, ErrorCategory.USER)


async def get_user(args: dict[str, Any]) -> ToolResult:
    """Get user information."""
    try:
        user_id = args.get("user_id", "")
        validate_user_id(user_id)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        result = await client.users_info(user_id)
        user = result.get("user", {})

        info = {
            "id": user.get("id"),
            "name": user.get("name"),
            "real_name": user.get("real_name", ""),
            "email": user.get("profile", {}).get("email", ""),
            "is_bot": user.get("is_bot", False),
            "is_admin": user.get("is_admin", False),
            "timezone": user.get("tz", ""),
        }

        return ToolResult(content=json.dumps(info, indent=2))

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("get_user", e, ErrorCategory.USER)


async def get_user_by_email(args: dict[str, Any]) -> ToolResult:
    """Get user by email."""
    try:
        email = args.get("email", "").strip()
        if not email:
            raise ValidationError("email is required")

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        result = await client.users_lookup_by_email(email)
        user = result.get("user", {})

        info = {
            "id": user.get("id"),
            "name": user.get("name"),
            "real_name": user.get("real_name", ""),
            "email": user.get("profile", {}).get("email", ""),
            "is_bot": user.get("is_bot", False),
            "is_admin": user.get("is_admin", False),
        }

        return ToolResult(content=json.dumps(info, indent=2))

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("get_user_by_email", e, ErrorCategory.USER)


async def open_dm(args: dict[str, Any]) -> ToolResult:
    """Open a DM conversation."""
    try:
        user_id = args.get("user_id", "")
        validate_user_id(user_id)

        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        result = await client.conversations_open(user_id)
        channel = result.get("channel", {})

        return ToolResult(
            content=json.dumps(
                {
                    "channel_id": channel.get("id"),
                    "user_id": user_id,
                },
                indent=2,
            )
        )

    except ValidationError as e:
        return ToolResult(content=str(e), is_error=True)
    except Exception as e:
        return log_and_format_error("open_dm", e, ErrorCategory.USER)


async def list_dms(args: dict[str, Any]) -> ToolResult:
    """List DM conversations."""
    try:
        client = get_client()
        if not client:
            return ToolResult(content="Slack client not initialized", is_error=True)

        result = await client.im_list()
        dms = result.get("ims", [])

        dm_list = []
        for dm in dms:
            dm_list.append(
                {
                    "id": dm.get("id"),
                    "user": dm.get("user"),
                    "is_open": dm.get("is_open", False),
                }
            )

        return ToolResult(content=json.dumps({"dms": dm_list}, indent=2))

    except Exception as e:
        return log_and_format_error("list_dms", e, ErrorCategory.USER)
