"""
Message API — organized by function category.

All functions are exported from this module for backward compatibility.
"""

from __future__ import annotations

from .delete import delete_message
from .draft import clear_draft, save_draft
from .edit import edit_message
from .forward import forward_message
from .get import get_drafts, get_messages
from .list import list_topics
from .mark import mark_as_read
from .pin import pin_message, unpin_message
from .poll import create_poll

# Import all functions from submodules
from .reaction import remove_reaction, send_reaction
from .reply import reply_to_message

__all__ = [
  "clear_draft",
  # Poll
  "create_poll",
  # Delete
  "delete_message",
  # Edit
  "edit_message",
  # Forward
  "forward_message",
  "get_drafts",
  # Get
  "get_messages",
  # List
  "list_topics",
  # Mark
  "mark_as_read",
  # Pin
  "pin_message",
  "remove_reaction",
  # Reply
  "reply_to_message",
  # Draft
  "save_draft",
  # Reactions
  "send_reaction",
  "unpin_message",
]
