"""
Message API — Telethon wrappers for message operations.

This module re-exports all functions from the message_api subdirectory
for backward compatibility.
"""

from __future__ import annotations

# Re-export all functions from the organized submodules
from .message_api import (
  send_reaction,
  remove_reaction,
  get_messages,
  get_drafts,
  edit_message,
  delete_message,
  forward_message,
  pin_message,
  unpin_message,
  mark_as_read,
  reply_to_message,
  save_draft,
  clear_draft,
  create_poll,
  list_topics,
)

__all__ = [
  "send_reaction",
  "remove_reaction",
  "get_messages",
  "get_drafts",
  "edit_message",
  "delete_message",
  "forward_message",
  "pin_message",
  "unpin_message",
  "mark_as_read",
  "reply_to_message",
  "save_draft",
  "clear_draft",
  "create_poll",
  "list_topics",
]
