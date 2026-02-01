"""
Input validation helpers for Slack skill tools.
"""

from __future__ import annotations


class ValidationError(Exception):
    """Raised when tool input validation fails."""

    pass


def validate_channel_id(channel_id: str) -> None:
    """Validate that channel_id is a valid Slack channel ID format."""
    if not channel_id:
        raise ValidationError("channel_id is required")
    if not isinstance(channel_id, str):
        raise ValidationError("channel_id must be a string")
    if not (channel_id.startswith("C") or channel_id.startswith("G")):
        raise ValidationError("channel_id must start with 'C' (public) or 'G' (private)")


def validate_user_id(user_id: str) -> None:
    """Validate that user_id is a valid Slack user ID format."""
    if not user_id:
        raise ValidationError("user_id is required")
    if not isinstance(user_id, str):
        raise ValidationError("user_id must be a string")
    if not user_id.startswith("U"):
        raise ValidationError("user_id must start with 'U'")


def validate_message_ts(message_ts: str) -> None:
    """Validate that message_ts is a valid Slack timestamp format."""
    if not message_ts:
        raise ValidationError("message_ts is required")
    if not isinstance(message_ts, str):
        raise ValidationError("message_ts must be a string")
    try:
        float(message_ts)
    except ValueError:
        raise ValidationError("message_ts must be a valid timestamp string")
