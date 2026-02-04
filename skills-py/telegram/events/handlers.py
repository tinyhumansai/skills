"""
Telethon event handler registration.

Delegates to focused sub-modules:
  - message_events: NewMessage, MessageEdited, MessageDeleted
  - chat_events: ChatAction (joins, leaves, kicks)
  - raw_events: Low-level updates (status, reads, drafts, pins, mute, typing, etc.)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .chat_events import register_chat_handlers
from .message_events import register_message_handlers
from .raw_events import register_raw_handlers

if TYPE_CHECKING:
  from telethon import TelegramClient

log = logging.getLogger("skill.telegram.events")


async def register_event_handlers(client: TelegramClient) -> None:
  """Register all Telethon event handlers on the given client."""
  await register_message_handlers(client)
  await register_chat_handlers(client)
  await register_raw_handlers(client)
  log.info("Event handlers registered")
