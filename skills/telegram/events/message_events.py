"""
Message event handlers — NewMessage, MessageEdited, MessageDeleted.

Each handler:
  1. Updates the in-memory store
  2. Persists to SQLite
  3. Logs to the events table
  4. Emits entity updates where applicable
"""

from __future__ import annotations

import logging
from typing import Any

from telethon import TelegramClient, events

from ..client.builders import build_message, build_peer_id
from ..state import store
from ..db.connection import get_db
from ..db.queries import (
  upsert_message,
  delete_message as db_delete_message,
  insert_event,
)
from ..entities import _chat_entity_type, _chat_metadata, _user_metadata, SOURCE

log = logging.getLogger("skill.telegram.events.messages")


async def register_message_handlers(client: TelegramClient) -> None:
  """Register message-related event handlers."""

  @client.on(events.NewMessage)
  async def on_new_message(event: events.NewMessage.Event) -> None:
    try:
      msg = event.message
      if msg is None:
        return

      chat_id = ""
      if msg.peer_id:
        chat_id = build_peer_id(msg.peer_id)

      telegram_msg = build_message(msg, fallback_chat_id=chat_id)
      if telegram_msg is None:
        return

      # Resolve sender name
      if telegram_msg.from_id:
        user = store.get_user(telegram_msg.from_id)
        if user:
          telegram_msg.from_name = user.first_name

      # Update in-memory store
      store.add_messages(chat_id, [telegram_msg])

      # Update chat's last message + unread count
      existing_chat = store.get_chat_by_id(chat_id)
      if existing_chat:
        updates: dict[str, Any] = {
          "last_message": telegram_msg,
          "last_message_date": telegram_msg.date,
        }
        if not telegram_msg.is_outgoing:
          updates["unread_count"] = existing_chat.unread_count + 1
        store.update_chat(chat_id, updates)

      # Persist to SQLite
      try:
        db = await get_db()
        await upsert_message(db, telegram_msg)
        await db.commit()
        await insert_event(
          db,
          "new_message",
          chat_id,
          {
            "message_id": telegram_msg.id,
            "from_id": telegram_msg.from_id,
            "text": telegram_msg.message[:200] if telegram_msg.message else "",
            "is_outgoing": telegram_msg.is_outgoing,
          },
        )
      except Exception:
        log.exception("Failed to persist new message to SQLite")

      # Incrementally update chat entity with new unread count
      try:
        from ..server import get_entity_callbacks

        upsert_entity_fn, upsert_rel_fn = get_entity_callbacks()
        if upsert_entity_fn:
          updated_chat = store.get_chat_by_id(chat_id)
          if updated_chat:
            await upsert_entity_fn(
              type=_chat_entity_type(updated_chat),
              source=SOURCE,
              source_id=updated_chat.id,
              title=updated_chat.title or f"Chat {updated_chat.id}",
              metadata=_chat_metadata(updated_chat),
            )

          # Upsert sender as contact if not already known
          if telegram_msg.from_id:
            sender = store.get_user(telegram_msg.from_id)
            if sender:
              await upsert_entity_fn(
                type="telegram.contact",
                source=SOURCE,
                source_id=sender.id,
                title=sender.first_name or f"User {sender.id}",
                metadata=_user_metadata(sender),
              )
      except Exception:
        log.debug("Failed to emit entity updates on new message", exc_info=True)

    except Exception:
      log.exception("Error in on_new_message handler")

  @client.on(events.MessageEdited)
  async def on_message_edited(event: events.MessageEdited.Event) -> None:
    try:
      msg = event.message
      if msg is None:
        return

      chat_id = ""
      if msg.peer_id:
        chat_id = build_peer_id(msg.peer_id)

      message_id = str(msg.id)

      # Update in-memory store
      store.update_message(
        chat_id,
        message_id,
        {
          "message": msg.message or "",
          "is_edited": True,
        },
      )

      # Persist to SQLite
      try:
        db = await get_db()
        telegram_msg = build_message(msg, fallback_chat_id=chat_id)
        if telegram_msg:
          await upsert_message(db, telegram_msg)
          await db.commit()
        await insert_event(
          db,
          "message_edited",
          chat_id,
          {
            "message_id": message_id,
            "new_text": (msg.message or "")[:200],
          },
        )
      except Exception:
        log.exception("Failed to persist edited message to SQLite")

    except Exception:
      log.exception("Error in on_message_edited handler")

  @client.on(events.MessageDeleted)
  async def on_message_deleted(event: events.MessageDeleted.Event) -> None:
    try:
      deleted_ids = event.deleted_ids or []
      if not deleted_ids:
        return

      # Try to determine chat_id from the event
      chat_id = ""
      if hasattr(event, "peer") and event.peer:
        chat_id = build_peer_id(event.peer)
      elif hasattr(event, "channel_id") and event.channel_id:
        chat_id = str(event.channel_id)

      str_ids = [str(mid) for mid in deleted_ids]

      # Update in-memory store
      if chat_id:
        store.delete_messages(chat_id, str_ids)

      # Persist to SQLite
      try:
        db = await get_db()
        for mid in str_ids:
          if chat_id:
            await db_delete_message(db, chat_id, mid)
        await insert_event(
          db,
          "message_deleted",
          chat_id or None,
          {
            "message_ids": str_ids,
          },
        )
      except Exception:
        log.exception("Failed to persist deleted messages to SQLite")

    except Exception:
      log.exception("Error in on_message_deleted handler")
