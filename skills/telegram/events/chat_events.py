"""
Chat action event handlers — user joins, leaves, kicks, etc.

Updates participants_count and emits entity updates for chat membership changes.
"""

from __future__ import annotations

import logging

from telethon import TelegramClient, events

from ..client.builders import build_peer_id
from ..state import store
from ..db.connection import get_db
from ..db.queries import insert_event
from ..entities import _chat_entity_type, _chat_metadata, SOURCE

log = logging.getLogger("skill.telegram.events.chat")


async def register_chat_handlers(client: TelegramClient) -> None:
  """Register chat action event handlers."""

  @client.on(events.ChatAction)
  async def on_chat_action(event: events.ChatAction.Event) -> None:
    try:
      chat_id = ""
      if hasattr(event, "chat_id") and event.chat_id:
        chat_id = str(event.chat_id)
      elif hasattr(event, "peer") and event.peer:
        chat_id = build_peer_id(event.peer)

      action_type = "unknown"
      if hasattr(event, "action_message") and event.action_message:
        action_type = type(event.action_message.action).__name__

      # Update users if someone joined/left
      if hasattr(event, "user_added") and event.user_added:
        action_type = "user_added"
      elif hasattr(event, "user_kicked") and event.user_kicked:
        action_type = "user_kicked"
      elif hasattr(event, "user_joined") and event.user_joined:
        action_type = "user_joined"
      elif hasattr(event, "user_left") and event.user_left:
        action_type = "user_left"

      # Try to update participants count
      existing_chat = store.get_chat_by_id(chat_id)
      if existing_chat and existing_chat.participants_count is not None:
        delta = 0
        if action_type in ("user_added", "user_joined"):
          delta = 1
        elif action_type in ("user_kicked", "user_left"):
          delta = -1
        if delta != 0:
          store.update_chat(
            chat_id,
            {"participants_count": max(0, existing_chat.participants_count + delta)},
          )

      # Persist event to SQLite
      try:
        db = await get_db()
        await insert_event(
          db,
          "chat_action",
          chat_id or None,
          {
            "action": action_type,
          },
        )
      except Exception:
        log.exception("Failed to persist chat action to SQLite")

      # Update chat entity with new participants count
      try:
        from ..server import get_entity_callbacks

        upsert_entity_fn, upsert_rel_fn = get_entity_callbacks()
        if upsert_entity_fn and chat_id:
          refreshed_chat = store.get_chat_by_id(chat_id)
          if refreshed_chat:
            await upsert_entity_fn(
              type=_chat_entity_type(refreshed_chat),
              source=SOURCE,
              source_id=refreshed_chat.id,
              title=refreshed_chat.title or f"Chat {refreshed_chat.id}",
              metadata=_chat_metadata(refreshed_chat),
            )
      except Exception:
        log.debug("Failed to emit entity updates on chat action", exc_info=True)

    except Exception:
      log.exception("Error in on_chat_action handler")
