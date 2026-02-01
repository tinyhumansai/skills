"""
Message API — organized by function category.

All functions are exported from this module for backward compatibility.
"""

from __future__ import annotations

# Import all functions from submodules
from .reaction import send_reaction, remove_reaction
from .get import get_messages, get_drafts
from .edit import edit_message
from .delete import delete_message
from .forward import forward_message
from .pin import pin_message, unpin_message
from .mark import mark_as_read
from .reply import reply_to_message
from .draft import save_draft, clear_draft
from .poll import create_poll
from .list import list_topics

__all__ = [
  # Reactions
  "send_reaction",
  "remove_reaction",
  # Get
  "get_messages",
  "get_drafts",
  # Edit
  "edit_message",
  # Delete
  "delete_message",
  # Forward
  "forward_message",
  # Pin
  "pin_message",
  "unpin_message",
  # Mark
  "mark_as_read",
  # Reply
  "reply_to_message",
  # Draft
  "save_draft",
  "clear_draft",
  # Poll
  "create_poll",
  # List
  "list_topics",
]
