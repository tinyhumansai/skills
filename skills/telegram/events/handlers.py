"""
Telethon event handlers for real-time update capture.

Registers handlers for NewMessage, MessageEdited, MessageDeleted,
ChatAction, UserUpdate, and MessageRead events. Each event:
  1. Updates the in-memory store
  2. Persists to SQLite
  3. Logs to the events table for the app to query
"""

from __future__ import annotations

import logging
import time
from typing import Any

from telethon import TelegramClient, events
from telethon.tl.types import (
    UpdateReadHistoryInbox,
    UpdateReadHistoryOutbox,
    UpdateReadChannelInbox,
    UpdateReadChannelOutbox,
    UpdateUserStatus,
    PeerUser,
    PeerChat,
    PeerChannel,
)

from ..client.builders import build_message, build_chat, build_peer_id, build_user, get_chat_type
from ..state import store
from ..state.types import TelegramMessage
from ..db.connection import get_db
from ..db.queries import (
    upsert_message,
    delete_message as db_delete_message,
    insert_event,
    upsert_chat,
)

log = logging.getLogger("skill.telegram.events")


async def register_event_handlers(client: TelegramClient) -> None:
    """Register all Telethon event handlers on the given client."""

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
                await insert_event(db, "new_message", chat_id, {
                    "message_id": telegram_msg.id,
                    "from_id": telegram_msg.from_id,
                    "text": telegram_msg.message[:200] if telegram_msg.message else "",
                    "is_outgoing": telegram_msg.is_outgoing,
                })
            except Exception:
                log.exception("Failed to persist new message to SQLite")

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
            store.update_message(chat_id, message_id, {
                "message": msg.message or "",
                "is_edited": True,
            })

            # Persist to SQLite
            try:
                db = await get_db()
                telegram_msg = build_message(msg, fallback_chat_id=chat_id)
                if telegram_msg:
                    await upsert_message(db, telegram_msg)
                    await db.commit()
                await insert_event(db, "message_edited", chat_id, {
                    "message_id": message_id,
                    "new_text": (msg.message or "")[:200],
                })
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
                await insert_event(db, "message_deleted", chat_id or None, {
                    "message_ids": str_ids,
                })
            except Exception:
                log.exception("Failed to persist deleted messages to SQLite")

        except Exception:
            log.exception("Error in on_message_deleted handler")

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
                    store.update_chat(chat_id, {
                        "participants_count": max(0, existing_chat.participants_count + delta)
                    })

            # Persist event to SQLite
            try:
                db = await get_db()
                await insert_event(db, "chat_action", chat_id or None, {
                    "action": action_type,
                })
            except Exception:
                log.exception("Failed to persist chat action to SQLite")

        except Exception:
            log.exception("Error in on_chat_action handler")

    @client.on(events.Raw)
    async def on_raw_update(event: Any) -> None:
        """Handle raw updates for events not covered by high-level handlers."""
        try:
            # User status updates
            if isinstance(event, UpdateUserStatus):
                user_id = str(event.user_id)
                status_name = type(event.status).__name__ if event.status else "unknown"
                try:
                    db = await get_db()
                    await insert_event(db, "user_status", None, {
                        "user_id": user_id,
                        "status": status_name,
                    })
                except Exception:
                    pass  # Non-critical
                return

            # Read receipts — inbox
            if isinstance(event, (UpdateReadHistoryInbox, UpdateReadChannelInbox)):
                chat_id = ""
                max_id = 0
                if isinstance(event, UpdateReadHistoryInbox):
                    chat_id = build_peer_id(event.peer)
                    max_id = event.max_id
                elif isinstance(event, UpdateReadChannelInbox):
                    chat_id = str(event.channel_id)
                    max_id = event.max_id

                if chat_id:
                    existing = store.get_chat_by_id(chat_id)
                    if existing:
                        # Reset unread — the server tells us the new count
                        unread = getattr(event, "still_unread_count", 0)
                        store.update_chat(chat_id, {"unread_count": unread})

                    try:
                        db = await get_db()
                        await insert_event(db, "messages_read", chat_id, {
                            "max_id": max_id,
                            "direction": "inbox",
                        })
                    except Exception:
                        pass
                return

            # Read receipts — outbox
            if isinstance(event, (UpdateReadHistoryOutbox, UpdateReadChannelOutbox)):
                chat_id = ""
                max_id = 0
                if isinstance(event, UpdateReadHistoryOutbox):
                    chat_id = build_peer_id(event.peer)
                    max_id = event.max_id
                elif isinstance(event, UpdateReadChannelOutbox):
                    chat_id = str(event.channel_id)
                    max_id = event.max_id

                if chat_id:
                    try:
                        db = await get_db()
                        await insert_event(db, "messages_read", chat_id, {
                            "max_id": max_id,
                            "direction": "outbox",
                        })
                    except Exception:
                        pass
                return

        except Exception:
            # Raw handler should never crash the client
            pass
