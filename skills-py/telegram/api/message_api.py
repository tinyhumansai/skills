"""
Message API — Telethon wrappers for message operations.

This module re-exports all functions from the message_api subdirectory
for backward compatibility.
"""

from __future__ import annotations

# Re-export all functions from the organized submodules
from .message_api import (
  clear_draft,
  create_poll,
  delete_message,
  edit_message,
  forward_message,
  get_drafts,
  get_messages,
  list_topics,
  mark_as_read,
  pin_message,
  remove_reaction,
  reply_to_message,
  save_draft,
  send_reaction,
  unpin_message,
)

__all__ = [
  "clear_draft",
  "create_poll",
  "delete_message",
  "edit_message",
  "forward_message",
  "get_drafts",
  "get_messages",
  "list_topics",
  "mark_as_read",
  "pin_message",
  "remove_reaction",
  "reply_to_message",
  "save_draft",
  "send_reaction",
  "unpin_message",
]
