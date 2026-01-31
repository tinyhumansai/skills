"""
Tool definitions for all 75+ Telegram tools.

Ported from tools.ts. Each tool has a name, description, and inputSchema.
"""

from __future__ import annotations

from mcp.types import Tool

# ---------------------------------------------------------------------------
# Chat tools
# ---------------------------------------------------------------------------

chat_tools: list[Tool] = [
    Tool(
        name="get_chats",
        description="Get a paginated list of chats",
        inputSchema={
            "type": "object",
            "properties": {
                "page": {"type": "number", "description": "Page number (1-indexed)", "default": 1},
                "page_size": {"type": "number", "description": "Number of chats per page", "default": 20},
            },
        },
    ),
    Tool(
        name="list_chats",
        description="List chats with optional type filter",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_type": {"type": "string", "description": "Filter by chat type: private, group, supergroup, channel", "enum": ["private", "group", "supergroup", "channel"]},
                "limit": {"type": "number", "description": "Maximum number of chats to return", "default": 20},
            },
        },
    ),
    Tool(
        name="get_chat",
        description="Get detailed information about a specific chat",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "The ID or username of the chat"},
            },
            "required": ["chat_id"],
        },
    ),
    Tool(
        name="create_group",
        description="Create a new group chat",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Group title"},
                "user_ids": {"type": "array", "items": {"type": "string"}, "description": "User IDs to add to the group"},
            },
            "required": ["title", "user_ids"],
        },
    ),
    Tool(
        name="invite_to_group",
        description="Invite users to a group chat",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "The ID or username of the group"},
                "user_ids": {"type": "array", "items": {"type": "string"}, "description": "User IDs to invite"},
            },
            "required": ["chat_id", "user_ids"],
        },
    ),
    Tool(
        name="create_channel",
        description="Create a new channel",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Channel title"},
                "description": {"type": "string", "description": "Channel description"},
                "megagroup": {"type": "boolean", "description": "Create as megagroup (supergroup) instead of channel", "default": False},
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="edit_chat_title",
        description="Edit the title of a chat/group/channel",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "The ID or username of the chat"},
                "new_title": {"type": "string", "description": "The new title"},
            },
            "required": ["chat_id", "new_title"],
        },
    ),
    Tool(
        name="delete_chat_photo",
        description="Delete the photo of a chat/group/channel",
        inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}}, "required": ["chat_id"]},
    ),
    Tool(
        name="leave_chat",
        description="Leave a group or channel",
        inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}}, "required": ["chat_id"]},
    ),
    Tool(
        name="get_invite_link",
        description="Get the invite link for a chat",
        inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}}, "required": ["chat_id"]},
    ),
    Tool(
        name="export_chat_invite",
        description="Create a new invite link for a chat",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "The ID or username of the chat"},
                "expire_date": {"type": "number", "description": "Unix timestamp when the link expires"},
                "usage_limit": {"type": "number", "description": "Maximum number of times the link can be used"},
            },
            "required": ["chat_id"],
        },
    ),
    Tool(
        name="import_chat_invite",
        description="Join a chat using an invite hash",
        inputSchema={"type": "object", "properties": {"invite_hash": {"type": "string", "description": "The invite hash from an invite link"}}, "required": ["invite_hash"]},
    ),
    Tool(
        name="join_chat_by_link",
        description="Join a chat using a full invite link",
        inputSchema={"type": "object", "properties": {"invite_link": {"type": "string", "description": "The full invite link (t.me/+xxx or t.me/joinchat/xxx)"}}, "required": ["invite_link"]},
    ),
    Tool(
        name="subscribe_public_channel",
        description="Subscribe to a public channel by username",
        inputSchema={"type": "object", "properties": {"username": {"type": "string", "description": "The channel username (without @)"}}, "required": ["username"]},
    ),
]

# ---------------------------------------------------------------------------
# Message tools
# ---------------------------------------------------------------------------

message_tools: list[Tool] = [
    Tool(name="get_messages", description="Get messages from a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "limit": {"type": "number", "description": "Number of messages to retrieve", "default": 20}, "offset": {"type": "number", "description": "Offset for pagination", "default": 0}}, "required": ["chat_id"]}),
    Tool(name="list_messages", description="List messages from a chat with formatting", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "limit": {"type": "number", "description": "Number of messages", "default": 20}}, "required": ["chat_id"]}),
    Tool(name="list_topics", description="List forum topics in a supergroup", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the supergroup"}}, "required": ["chat_id"]}),
    Tool(name="send_message", description="Send a message to a specific chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message": {"type": "string", "description": "The message content to send"}}, "required": ["chat_id", "message"]}),
    Tool(name="reply_to_message", description="Reply to a specific message in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The ID of the message to reply to"}, "text": {"type": "string", "description": "The reply text"}}, "required": ["chat_id", "message_id", "text"]}),
    Tool(name="edit_message", description="Edit an existing message", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The ID of the message to edit"}, "new_text": {"type": "string", "description": "The new message text"}}, "required": ["chat_id", "message_id", "new_text"]}),
    Tool(name="delete_message", description="Delete a message from a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The ID of the message to delete"}, "revoke": {"type": "boolean", "description": "Delete for everyone (not just yourself)", "default": True}}, "required": ["chat_id", "message_id"]}),
    Tool(name="forward_message", description="Forward a message from one chat to another", inputSchema={"type": "object", "properties": {"from_chat_id": {"type": "string", "description": "Source chat ID or username"}, "to_chat_id": {"type": "string", "description": "Destination chat ID or username"}, "message_id": {"type": "number", "description": "The ID of the message to forward"}}, "required": ["from_chat_id", "to_chat_id", "message_id"]}),
    Tool(name="pin_message", description="Pin a message in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The ID of the message to pin"}, "notify": {"type": "boolean", "description": "Send notification about the pin", "default": True}}, "required": ["chat_id", "message_id"]}),
    Tool(name="unpin_message", description="Unpin a message in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The ID of the message to unpin"}}, "required": ["chat_id", "message_id"]}),
    Tool(name="mark_as_read", description="Mark messages as read in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}}, "required": ["chat_id"]}),
    Tool(name="get_message_context", description="Get messages surrounding a specific message", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The central message ID"}, "limit": {"type": "number", "description": "Number of messages before and after", "default": 5}}, "required": ["chat_id", "message_id"]}),
    Tool(name="get_history", description="Get message history from a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "limit": {"type": "number", "description": "Number of messages", "default": 20}, "offset_id": {"type": "number", "description": "Offset message ID for pagination"}}, "required": ["chat_id"]}),
    Tool(name="get_pinned_messages", description="Get pinned messages in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}}, "required": ["chat_id"]}),
    Tool(name="send_reaction", description="Add a reaction to a message", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The message ID"}, "reaction": {"type": "string", "description": "The reaction emoji", "default": "\ud83d\udc4d"}}, "required": ["chat_id", "message_id"]}),
    Tool(name="remove_reaction", description="Remove a reaction from a message", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The message ID"}, "reaction": {"type": "string", "description": "The reaction emoji to remove"}}, "required": ["chat_id", "message_id"]}),
    Tool(name="get_message_reactions", description="Get reactions on a message", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The message ID"}}, "required": ["chat_id", "message_id"]}),
    Tool(name="list_inline_buttons", description="List inline keyboard buttons on a message", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The message ID"}}, "required": ["chat_id", "message_id"]}),
    Tool(name="press_inline_button", description="Press an inline keyboard button on a message", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The message ID"}, "button_index": {"type": "number", "description": "The index of the button to press (0-based)"}, "button_text": {"type": "string", "description": "The text of the button to press (alternative to index)"}}, "required": ["chat_id", "message_id"]}),
    Tool(name="save_draft", description="Save a draft message in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "text": {"type": "string", "description": "The draft message text"}, "reply_to_message_id": {"type": "number", "description": "Optional message ID to reply to"}}, "required": ["chat_id", "text"]}),
    Tool(name="get_drafts", description="Get all draft messages", inputSchema={"type": "object", "properties": {}}),
    Tool(name="clear_draft", description="Clear a draft message in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}}, "required": ["chat_id"]}),
    Tool(name="create_poll", description="Create a poll in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "question": {"type": "string", "description": "The poll question"}, "options": {"type": "array", "items": {"type": "string"}, "description": "The poll options"}, "anonymous": {"type": "boolean", "description": "Whether the poll is anonymous", "default": True}, "multiple_choice": {"type": "boolean", "description": "Allow multiple answers", "default": False}, "quiz": {"type": "boolean", "description": "Whether this is a quiz", "default": False}, "correct_option": {"type": "number", "description": "Index of the correct option (for quiz mode)"}}, "required": ["chat_id", "question", "options"]}),
]

# ---------------------------------------------------------------------------
# Contact tools
# ---------------------------------------------------------------------------

contact_tools: list[Tool] = [
    Tool(name="list_contacts", description="Get a list of contacts", inputSchema={"type": "object", "properties": {"limit": {"type": "number", "description": "Maximum number of contacts", "default": 20}}}),
    Tool(name="search_contacts", description="Search contacts by name or username", inputSchema={"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}, "limit": {"type": "number", "description": "Maximum results", "default": 20}}, "required": ["query"]}),
    Tool(name="add_contact", description="Add a new contact", inputSchema={"type": "object", "properties": {"first_name": {"type": "string", "description": "Contact's first name"}, "last_name": {"type": "string", "description": "Contact's last name"}, "phone_number": {"type": "string", "description": "Contact's phone number"}, "user_id": {"type": "string", "description": "User ID (alternative to phone number)"}}, "required": ["first_name", "phone_number"]}),
    Tool(name="delete_contact", description="Delete a contact", inputSchema={"type": "object", "properties": {"user_id": {"type": "string", "description": "The user ID to delete"}}, "required": ["user_id"]}),
    Tool(name="block_user", description="Block a user", inputSchema={"type": "object", "properties": {"user_id": {"type": "string", "description": "The user ID to block"}}, "required": ["user_id"]}),
    Tool(name="unblock_user", description="Unblock a user", inputSchema={"type": "object", "properties": {"user_id": {"type": "string", "description": "The user ID to unblock"}}, "required": ["user_id"]}),
    Tool(name="get_blocked_users", description="Get a list of blocked users", inputSchema={"type": "object", "properties": {"limit": {"type": "number", "description": "Maximum number of blocked users", "default": 100}}}),
    Tool(name="get_contact_ids", description="Get IDs of all contacts", inputSchema={"type": "object", "properties": {}}),
    Tool(name="import_contacts", description="Import contacts from a list of phone numbers", inputSchema={"type": "object", "properties": {"contacts": {"type": "array", "items": {"type": "object", "properties": {"phone": {"type": "string"}, "first_name": {"type": "string"}, "last_name": {"type": "string"}}}, "description": "Array of contacts with phone, first_name, last_name"}}, "required": ["contacts"]}),
    Tool(name="export_contacts", description="Export all contacts", inputSchema={"type": "object", "properties": {}}),
    Tool(name="get_direct_chat_by_contact", description="Get the direct chat with a specific contact", inputSchema={"type": "object", "properties": {"user_id": {"type": "string", "description": "The user ID of the contact"}}, "required": ["user_id"]}),
    Tool(name="get_contact_chats", description="Get all chats that are direct conversations with contacts", inputSchema={"type": "object", "properties": {"limit": {"type": "number", "description": "Maximum number of chats", "default": 20}}}),
    Tool(name="get_last_interaction", description="Get the last interaction with a user across all chats", inputSchema={"type": "object", "properties": {"user_id": {"type": "string", "description": "The user ID"}}, "required": ["user_id"]}),
]

# ---------------------------------------------------------------------------
# Admin tools
# ---------------------------------------------------------------------------

admin_tools: list[Tool] = [
    Tool(name="get_participants", description="Get participants of a chat/group/channel", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "limit": {"type": "number", "description": "Maximum participants", "default": 100}, "filter": {"type": "string", "description": "Filter type: recent, admins, kicked, bots", "default": "recent"}}, "required": ["chat_id"]}),
    Tool(name="get_admins", description="Get administrators of a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}}, "required": ["chat_id"]}),
    Tool(name="get_banned_users", description="Get banned users in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "limit": {"type": "number", "description": "Maximum results", "default": 100}}, "required": ["chat_id"]}),
    Tool(name="promote_admin", description="Promote a user to admin", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "user_id": {"type": "string", "description": "The user ID to promote"}, "title": {"type": "string", "description": "Custom admin title"}}, "required": ["chat_id", "user_id"]}),
    Tool(name="demote_admin", description="Demote an admin to regular user", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "user_id": {"type": "string", "description": "The user ID to demote"}}, "required": ["chat_id", "user_id"]}),
    Tool(name="ban_user", description="Ban a user from a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "user_id": {"type": "string", "description": "The user ID to ban"}, "until_date": {"type": "number", "description": "Unix timestamp when the ban expires (0 for permanent)"}}, "required": ["chat_id", "user_id"]}),
    Tool(name="unban_user", description="Unban a user in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "user_id": {"type": "string", "description": "The user ID to unban"}}, "required": ["chat_id", "user_id"]}),
    Tool(name="get_recent_actions", description="Get recent admin actions in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "limit": {"type": "number", "description": "Maximum actions", "default": 20}}, "required": ["chat_id"]}),
]

# ---------------------------------------------------------------------------
# Profile & Media tools
# ---------------------------------------------------------------------------

profile_media_tools: list[Tool] = [
    Tool(name="get_me", description="Get information about the current user", inputSchema={"type": "object", "properties": {}}),
    Tool(name="update_profile", description="Update the current user's profile", inputSchema={"type": "object", "properties": {"first_name": {"type": "string", "description": "New first name"}, "last_name": {"type": "string", "description": "New last name"}, "bio": {"type": "string", "description": "New bio/about text"}}}),
    Tool(name="get_user_photos", description="Get profile photos of a user", inputSchema={"type": "object", "properties": {"user_id": {"type": "string", "description": "The user ID"}, "limit": {"type": "number", "description": "Maximum photos", "default": 20}}, "required": ["user_id"]}),
    Tool(name="get_user_status", description="Get the online status of a user", inputSchema={"type": "object", "properties": {"user_id": {"type": "string", "description": "The user ID"}}, "required": ["user_id"]}),
    Tool(name="set_profile_photo", description="Set a profile photo (from file path or URL)", inputSchema={"type": "object", "properties": {"file_path": {"type": "string", "description": "Local file path to the photo"}, "url": {"type": "string", "description": "URL to download the photo from"}}}),
    Tool(name="delete_profile_photo", description="Delete the current profile photo", inputSchema={"type": "object", "properties": {"photo_id": {"type": "string", "description": "Specific photo ID to delete (optional, deletes current if not specified)"}}}),
    Tool(name="edit_chat_photo", description="Set a chat/group/channel photo", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "file_path": {"type": "string", "description": "Local file path to the photo"}}, "required": ["chat_id"]}),
    Tool(name="get_media_info", description="Get media information from a message", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "message_id": {"type": "number", "description": "The message ID"}}, "required": ["chat_id", "message_id"]}),
    Tool(name="get_bot_info", description="Get information about a bot in a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The chat ID or bot username"}}, "required": ["chat_id"]}),
    Tool(name="set_bot_commands", description="Set bot commands for a scope", inputSchema={"type": "object", "properties": {"commands": {"type": "array", "items": {"type": "object", "properties": {"command": {"type": "string"}, "description": {"type": "string"}}}, "description": "Array of command objects"}, "chat_id": {"type": "string", "description": "Optional chat to scope the commands to"}}, "required": ["commands"]}),
    Tool(name="get_sticker_sets", description="Get installed sticker sets", inputSchema={"type": "object", "properties": {"limit": {"type": "number", "description": "Maximum sticker sets", "default": 20}}}),
    Tool(name="get_gif_search", description="Search for GIFs", inputSchema={"type": "object", "properties": {"query": {"type": "string", "description": "Search query for GIFs"}, "limit": {"type": "number", "description": "Maximum results", "default": 20}}, "required": ["query"]}),
]

# ---------------------------------------------------------------------------
# Settings tools
# ---------------------------------------------------------------------------

settings_tools: list[Tool] = [
    Tool(name="mute_chat", description="Mute notifications for a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}, "mute_for": {"type": "number", "description": "Mute duration in seconds (0 for forever)"}}, "required": ["chat_id"]}),
    Tool(name="unmute_chat", description="Unmute notifications for a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}}, "required": ["chat_id"]}),
    Tool(name="archive_chat", description="Archive a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}}, "required": ["chat_id"]}),
    Tool(name="unarchive_chat", description="Unarchive a chat", inputSchema={"type": "object", "properties": {"chat_id": {"type": "string", "description": "The ID or username of the chat"}}, "required": ["chat_id"]}),
    Tool(name="get_privacy_settings", description="Get privacy settings", inputSchema={"type": "object", "properties": {}}),
    Tool(name="set_privacy_settings", description="Update privacy settings", inputSchema={"type": "object", "properties": {"setting": {"type": "string", "description": "The privacy setting to change (e.g., 'phone_number', 'last_seen', 'profile_photo')"}, "value": {"type": "string", "description": "The new value (e.g., 'everybody', 'contacts', 'nobody')"}}, "required": ["setting", "value"]}),
]

# ---------------------------------------------------------------------------
# Search tools
# ---------------------------------------------------------------------------

search_tools: list[Tool] = [
    Tool(name="search_public_chats", description="Search for public chats/channels by query", inputSchema={"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}, "limit": {"type": "number", "description": "Maximum results", "default": 20}}, "required": ["query"]}),
    Tool(name="search_messages", description="Search messages in a chat or globally", inputSchema={"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}, "chat_id": {"type": "string", "description": "Optional chat ID to search in (omit for global search)"}, "limit": {"type": "number", "description": "Maximum results", "default": 20}}, "required": ["query"]}),
    Tool(name="resolve_username", description="Resolve a username to get user/channel info", inputSchema={"type": "object", "properties": {"username": {"type": "string", "description": "The username to resolve (without @)"}}, "required": ["username"]}),
]

# ---------------------------------------------------------------------------
# All tools combined
# ---------------------------------------------------------------------------

ALL_TOOLS: list[Tool] = [
    *chat_tools,
    *message_tools,
    *contact_tools,
    *admin_tools,
    *profile_media_tools,
    *settings_tools,
    *search_tools,
]
