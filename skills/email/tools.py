"""
Tool definitions for all 35 email tools.

Each tool has a name, description, and inputSchema.
"""

from __future__ import annotations

from mcp.types import Tool

# ---------------------------------------------------------------------------
# Folder tools (5)
# ---------------------------------------------------------------------------

folder_tools: list[Tool] = [
    Tool(
        name="list_folders",
        description="List all IMAP mailbox folders",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Filter folders by name pattern"},
            },
        },
    ),
    Tool(
        name="get_folder_status",
        description="Get message counts (total, unseen, recent) for a folder",
        inputSchema={
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Folder name (e.g. INBOX)"},
            },
            "required": ["folder"],
        },
    ),
    Tool(
        name="create_folder",
        description="Create a new IMAP folder",
        inputSchema={
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Name of the folder to create"},
            },
            "required": ["folder"],
        },
    ),
    Tool(
        name="rename_folder",
        description="Rename an existing IMAP folder",
        inputSchema={
            "type": "object",
            "properties": {
                "old_name": {"type": "string", "description": "Current folder name"},
                "new_name": {"type": "string", "description": "New folder name"},
            },
            "required": ["old_name", "new_name"],
        },
    ),
    Tool(
        name="delete_folder",
        description="Delete an empty IMAP folder",
        inputSchema={
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Name of the folder to delete"},
            },
            "required": ["folder"],
        },
    ),
]

# ---------------------------------------------------------------------------
# Message read tools (7)
# ---------------------------------------------------------------------------

message_tools: list[Tool] = [
    Tool(
        name="list_messages",
        description="List email message summaries in a folder",
        inputSchema={
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
                "limit": {"type": "number", "description": "Maximum messages to return", "default": 20},
                "offset": {"type": "number", "description": "Offset for pagination", "default": 0},
                "sort": {"type": "string", "description": "Sort order: date_desc or date_asc", "default": "date_desc"},
            },
        },
    ),
    Tool(
        name="get_message",
        description="Get full email message content including body",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "number", "description": "The UID of the message"},
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
                "format": {"type": "string", "description": "Body format: text, html, or raw", "default": "text"},
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="search_messages",
        description="Search emails by content, sender, subject, date, or other criteria",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text search query"},
                "folder": {"type": "string", "description": "Folder to search in (omit for INBOX)"},
                "limit": {"type": "number", "description": "Maximum results", "default": 20},
                "from_addr": {"type": "string", "description": "Filter by sender email address"},
                "to_addr": {"type": "string", "description": "Filter by recipient email address"},
                "subject": {"type": "string", "description": "Filter by subject text"},
                "since": {"type": "string", "description": "Messages after this date (DD-Mon-YYYY)"},
                "before": {"type": "string", "description": "Messages before this date (DD-Mon-YYYY)"},
                "has_attachment": {"type": "boolean", "description": "Filter for messages with attachments"},
            },
        },
    ),
    Tool(
        name="get_unread_messages",
        description="Get unread messages in a folder",
        inputSchema={
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
                "limit": {"type": "number", "description": "Maximum messages", "default": 20},
            },
        },
    ),
    Tool(
        name="get_thread",
        description="Get all messages in an email thread",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "number", "description": "UID of any message in the thread"},
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="count_messages",
        description="Get the message count for a folder",
        inputSchema={
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
            },
        },
    ),
    Tool(
        name="get_recent_messages",
        description="Get messages received in the last N hours",
        inputSchema={
            "type": "object",
            "properties": {
                "hours": {"type": "number", "description": "Number of hours to look back", "default": 24},
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
                "limit": {"type": "number", "description": "Maximum messages", "default": 20},
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# Send tools (3)
# ---------------------------------------------------------------------------

send_tools: list[Tool] = [
    Tool(
        name="send_email",
        description="Compose and send a new email",
        inputSchema={
            "type": "object",
            "properties": {
                "to": {
                    "oneOf": [
                        {"type": "string", "description": "Recipient email (or comma-separated list)"},
                        {"type": "array", "items": {"type": "string"}, "description": "List of recipient emails"},
                    ],
                    "description": "Recipient email address(es)",
                },
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Plain text body"},
                "cc": {"type": "array", "items": {"type": "string"}, "description": "CC recipients"},
                "bcc": {"type": "array", "items": {"type": "string"}, "description": "BCC recipients"},
                "html_body": {"type": "string", "description": "HTML body (alternative to plain text)"},
                "reply_to": {"type": "string", "description": "Reply-To address"},
            },
            "required": ["to", "subject", "body"],
        },
    ),
    Tool(
        name="reply_to_email",
        description="Reply to an email, preserving thread headers (In-Reply-To, References)",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "number", "description": "UID of the message to reply to"},
                "body": {"type": "string", "description": "Reply body text"},
                "folder": {"type": "string", "description": "Folder containing the message", "default": "INBOX"},
                "reply_all": {"type": "boolean", "description": "Reply to all recipients", "default": False},
                "html_body": {"type": "string", "description": "HTML reply body"},
            },
            "required": ["message_id", "body"],
        },
    ),
    Tool(
        name="forward_email",
        description="Forward an email to new recipients",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "number", "description": "UID of the message to forward"},
                "to": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ],
                    "description": "Recipient email address(es)",
                },
                "folder": {"type": "string", "description": "Folder containing the message", "default": "INBOX"},
                "body": {"type": "string", "description": "Additional message above forwarded content"},
                "html_body": {"type": "string", "description": "HTML body"},
            },
            "required": ["message_id", "to"],
        },
    ),
]

# ---------------------------------------------------------------------------
# Flag/manage tools (7)
# ---------------------------------------------------------------------------

flag_tools: list[Tool] = [
    Tool(
        name="mark_read",
        description="Mark email messages as read",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "oneOf": [
                        {"type": "number"},
                        {"type": "array", "items": {"type": "number"}},
                    ],
                    "description": "UID(s) of messages to mark as read",
                },
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
            },
            "required": ["message_ids"],
        },
    ),
    Tool(
        name="mark_unread",
        description="Mark email messages as unread",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "oneOf": [
                        {"type": "number"},
                        {"type": "array", "items": {"type": "number"}},
                    ],
                    "description": "UID(s) of messages to mark as unread",
                },
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
            },
            "required": ["message_ids"],
        },
    ),
    Tool(
        name="flag_message",
        description="Star/flag email messages",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "oneOf": [
                        {"type": "number"},
                        {"type": "array", "items": {"type": "number"}},
                    ],
                    "description": "UID(s) of messages to flag",
                },
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
            },
            "required": ["message_ids"],
        },
    ),
    Tool(
        name="unflag_message",
        description="Remove star/flag from email messages",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "oneOf": [
                        {"type": "number"},
                        {"type": "array", "items": {"type": "number"}},
                    ],
                    "description": "UID(s) of messages to unflag",
                },
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
            },
            "required": ["message_ids"],
        },
    ),
    Tool(
        name="delete_message",
        description="Move email messages to Trash",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "oneOf": [
                        {"type": "number"},
                        {"type": "array", "items": {"type": "number"}},
                    ],
                    "description": "UID(s) of messages to delete",
                },
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
            },
            "required": ["message_ids"],
        },
    ),
    Tool(
        name="move_message",
        description="Move email messages to another folder",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "oneOf": [
                        {"type": "number"},
                        {"type": "array", "items": {"type": "number"}},
                    ],
                    "description": "UID(s) of messages to move",
                },
                "destination": {"type": "string", "description": "Destination folder name"},
                "folder": {"type": "string", "description": "Source folder name", "default": "INBOX"},
            },
            "required": ["message_ids", "destination"],
        },
    ),
    Tool(
        name="archive_message",
        description="Move email messages to Archive",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "oneOf": [
                        {"type": "number"},
                        {"type": "array", "items": {"type": "number"}},
                    ],
                    "description": "UID(s) of messages to archive",
                },
                "folder": {"type": "string", "description": "Source folder name", "default": "INBOX"},
            },
            "required": ["message_ids"],
        },
    ),
]

# ---------------------------------------------------------------------------
# Attachment tools (3)
# ---------------------------------------------------------------------------

attachment_tools: list[Tool] = [
    Tool(
        name="list_attachments",
        description="List attachments on an email message",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "number", "description": "UID of the message"},
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="get_attachment_info",
        description="Get metadata for a specific attachment",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "number", "description": "UID of the message"},
                "attachment_index": {"type": "number", "description": "Index of the attachment (0-based)"},
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
            },
            "required": ["message_id", "attachment_index"],
        },
    ),
    Tool(
        name="save_attachment",
        description="Save an attachment to the skill's data directory",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "number", "description": "UID of the message"},
                "attachment_index": {"type": "number", "description": "Index of the attachment (0-based)"},
                "folder": {"type": "string", "description": "Folder name", "default": "INBOX"},
                "filename": {"type": "string", "description": "Override filename for saving"},
            },
            "required": ["message_id", "attachment_index"],
        },
    ),
]

# ---------------------------------------------------------------------------
# Draft tools (4)
# ---------------------------------------------------------------------------

draft_tools: list[Tool] = [
    Tool(
        name="save_draft",
        description="Save a draft email to the Drafts folder",
        inputSchema={
            "type": "object",
            "properties": {
                "to": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ],
                    "description": "Recipient email address(es)",
                },
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Plain text body"},
                "cc": {"type": "array", "items": {"type": "string"}, "description": "CC recipients"},
                "bcc": {"type": "array", "items": {"type": "string"}, "description": "BCC recipients"},
                "html_body": {"type": "string", "description": "HTML body"},
            },
            "required": ["to", "subject", "body"],
        },
    ),
    Tool(
        name="list_drafts",
        description="List draft email messages",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "number", "description": "Maximum drafts to return", "default": 20},
            },
        },
    ),
    Tool(
        name="update_draft",
        description="Update an existing draft email",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "number", "description": "UID of the draft to update"},
                "to": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ],
                    "description": "New recipient(s)",
                },
                "subject": {"type": "string", "description": "New subject"},
                "body": {"type": "string", "description": "New body text"},
                "html_body": {"type": "string", "description": "New HTML body"},
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="delete_draft",
        description="Delete a draft email",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "number", "description": "UID of the draft to delete"},
            },
            "required": ["message_id"],
        },
    ),
]

# ---------------------------------------------------------------------------
# Account tools (6)
# ---------------------------------------------------------------------------

account_tools: list[Tool] = [
    Tool(
        name="get_account_info",
        description="Get information about the connected email account",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_mailbox_summary",
        description="Get all folders with message and unread counts",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_unread_count",
        description="Get total unread message count across folders",
        inputSchema={
            "type": "object",
            "properties": {
                "folders": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific folders to check (omit for all)",
                },
            },
        },
    ),
    Tool(
        name="test_connection",
        description="Test IMAP and SMTP connectivity",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_sync_status",
        description="Get current sync and polling status",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="search_contacts",
        description="Search previously-seen email addresses",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (matches email or name)"},
                "limit": {"type": "number", "description": "Maximum results", "default": 20},
            },
            "required": ["query"],
        },
    ),
]

# ---------------------------------------------------------------------------
# All tools combined
# ---------------------------------------------------------------------------

ALL_TOOLS: list[Tool] = [
    *folder_tools,
    *message_tools,
    *send_tools,
    *flag_tools,
    *attachment_tools,
    *draft_tools,
    *account_tools,
]
