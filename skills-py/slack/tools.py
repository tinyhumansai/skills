"""
Slack tool definitions.
"""

from __future__ import annotations

TOOL_DEFINITIONS: list[tuple[str, str, dict]] = [
  # ---------------------------------------------------------------------------
  # Channel tools
  # ---------------------------------------------------------------------------
  (
    "list_channels",
    "List Slack channels (public and/or private).",
    {
      "type": "object",
      "properties": {
        "include_private": {
          "type": "boolean",
          "description": "Include private channels (default false).",
          "default": False,
        },
        "include_archived": {
          "type": "boolean",
          "description": "Include archived channels (default false).",
          "default": False,
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of channels to return (default 50).",
          "default": 50,
        },
      },
    },
  ),
  (
    "get_channel",
    "Get detailed information about a Slack channel.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel ID (e.g., C1234567890).",
        },
      },
      "required": ["channel_id"],
    },
  ),
  (
    "create_channel",
    "Create a new Slack channel.",
    {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "Channel name (lowercase, no spaces).",
        },
        "is_private": {
          "type": "boolean",
          "description": "Create as private channel (default false).",
          "default": False,
        },
      },
      "required": ["name"],
    },
  ),
  (
    "join_channel",
    "Join a Slack channel.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel ID to join.",
        },
      },
      "required": ["channel_id"],
    },
  ),
  (
    "leave_channel",
    "Leave a Slack channel.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel ID to leave.",
        },
      },
      "required": ["channel_id"],
    },
  ),
  (
    "archive_channel",
    "Archive a Slack channel.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel ID to archive.",
        },
      },
      "required": ["channel_id"],
    },
  ),
  (
    "unarchive_channel",
    "Unarchive a Slack channel.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel ID to unarchive.",
        },
      },
      "required": ["channel_id"],
    },
  ),
  (
    "set_channel_topic",
    "Set the topic of a Slack channel.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel ID.",
        },
        "topic": {
          "type": "string",
          "description": "The new topic text.",
        },
      },
      "required": ["channel_id", "topic"],
    },
  ),
  (
    "set_channel_purpose",
    "Set the purpose of a Slack channel.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel ID.",
        },
        "purpose": {
          "type": "string",
          "description": "The new purpose text.",
        },
      },
      "required": ["channel_id", "purpose"],
    },
  ),
  (
    "get_channel_members",
    "Get members of a Slack channel.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel ID.",
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of members to return (default 100).",
          "default": 100,
        },
      },
      "required": ["channel_id"],
    },
  ),
  # ---------------------------------------------------------------------------
  # Message tools
  # ---------------------------------------------------------------------------
  (
    "send_message",
    "Send a message to a Slack channel or DM.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel or DM ID.",
        },
        "text": {
          "type": "string",
          "description": "The message text.",
        },
        "thread_ts": {
          "type": "string",
          "description": "Optional thread timestamp to reply in thread.",
        },
      },
      "required": ["channel_id", "text"],
    },
  ),
  (
    "get_messages",
    "Get messages from a Slack channel or DM.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel or DM ID.",
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of messages (default 50).",
          "default": 50,
        },
        "oldest": {
          "type": "string",
          "description": "Oldest message timestamp to include.",
        },
        "latest": {
          "type": "string",
          "description": "Latest message timestamp to include.",
        },
      },
      "required": ["channel_id"],
    },
  ),
  (
    "edit_message",
    "Edit an existing Slack message.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel or DM ID.",
        },
        "message_ts": {
          "type": "string",
          "description": "The message timestamp.",
        },
        "text": {
          "type": "string",
          "description": "The new message text.",
        },
      },
      "required": ["channel_id", "message_ts", "text"],
    },
  ),
  (
    "delete_message",
    "Delete a Slack message.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel or DM ID.",
        },
        "message_ts": {
          "type": "string",
          "description": "The message timestamp.",
        },
      },
      "required": ["channel_id", "message_ts"],
    },
  ),
  (
    "get_message_permalink",
    "Get a permalink URL for a Slack message.",
    {
      "type": "object",
      "properties": {
        "channel_id": {
          "type": "string",
          "description": "The channel ID.",
        },
        "message_ts": {
          "type": "string",
          "description": "The message timestamp.",
        },
      },
      "required": ["channel_id", "message_ts"],
    },
  ),
  # ---------------------------------------------------------------------------
  # User tools
  # ---------------------------------------------------------------------------
  (
    "list_users",
    "List users in the Slack workspace.",
    {
      "type": "object",
      "properties": {
        "limit": {
          "type": "number",
          "description": "Maximum number of users to return (default 100).",
          "default": 100,
        },
      },
    },
  ),
  (
    "get_user",
    "Get information about a Slack user.",
    {
      "type": "object",
      "properties": {
        "user_id": {
          "type": "string",
          "description": "The user ID (e.g., U1234567890).",
        },
      },
      "required": ["user_id"],
    },
  ),
  (
    "get_user_by_email",
    "Look up a Slack user by email address.",
    {
      "type": "object",
      "properties": {
        "email": {
          "type": "string",
          "description": "The user's email address.",
        },
      },
      "required": ["email"],
    },
  ),
  # ---------------------------------------------------------------------------
  # DM tools
  # ---------------------------------------------------------------------------
  (
    "open_dm",
    "Open or resume a direct message conversation with a user.",
    {
      "type": "object",
      "properties": {
        "user_id": {
          "type": "string",
          "description": "The user ID to message.",
        },
      },
      "required": ["user_id"],
    },
  ),
  (
    "list_dms",
    "List direct message conversations.",
    {
      "type": "object",
      "properties": {},
    },
  ),
  # ---------------------------------------------------------------------------
  # Search tools
  # ---------------------------------------------------------------------------
  (
    "search_messages",
    "Search for messages across Slack.",
    {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query string.",
        },
        "count": {
          "type": "number",
          "description": "Maximum number of results (default 20).",
          "default": 20,
        },
      },
      "required": ["query"],
    },
  ),
  (
    "search_all",
    "Search for messages and files across Slack.",
    {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query string.",
        },
        "count": {
          "type": "number",
          "description": "Maximum number of results (default 20).",
          "default": 20,
        },
      },
      "required": ["query"],
    },
  ),
  # ---------------------------------------------------------------------------
  # Workspace tools
  # ---------------------------------------------------------------------------
  (
    "get_workspace_info",
    "Get information about the Slack workspace (team).",
    {
      "type": "object",
      "properties": {},
    },
  ),
]
