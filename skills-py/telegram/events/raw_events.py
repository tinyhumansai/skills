"""
Raw update handlers for events not covered by Telethon's high-level API.

Handles: user status, read receipts, drafts, pins, mute/notify settings,
typing indicators, channel metadata, archived folders, pinned messages,
and message content reads.
"""

from __future__ import annotations

import logging
from typing import Any

from telethon import TelegramClient, events
from telethon.tl.types import (
  DialogPeer,
  DraftMessage,
  DraftMessageEmpty,
  NotifyPeer,
  UpdateChannel,
  UpdateChannelReadMessagesContents,
  UpdateChannelUserTyping,
  UpdateChatParticipants,
  UpdateChatUserTyping,
  UpdateDeleteChannelMessages,
  UpdateDeleteMessages,
  UpdateDialogPinned,
  UpdateDraftMessage,
  UpdateFolderPeers,
  UpdateNotifySettings,
  UpdatePinnedChannelMessages,
  UpdatePinnedDialogs,
  UpdatePinnedMessages,
  UpdateReadChannelInbox,
  UpdateReadChannelOutbox,
  UpdateReadHistoryInbox,
  UpdateReadHistoryOutbox,
  UpdateReadMessagesContents,
  UpdateUserStatus,
  UpdateUserTyping,
)

from ..client.builders import build_peer_id
from ..db.connection import get_db
from ..db.queries import insert_event
from ..state import store

log = logging.getLogger("skill.telegram.events.raw")


async def register_raw_handlers(client: TelegramClient) -> None:
  """Register raw update event handlers."""

  @client.on(events.Raw)
  async def on_raw_update(event: Any) -> None:
    """Dispatch raw updates to specific handlers."""
    try:
      # User status updates
      if isinstance(event, UpdateUserStatus):
        await _handle_user_status(event)
        return

      # Read receipts — inbox
      if isinstance(event, (UpdateReadHistoryInbox, UpdateReadChannelInbox)):
        await _handle_read_inbox(event)
        return

      # Read receipts — outbox
      if isinstance(event, (UpdateReadHistoryOutbox, UpdateReadChannelOutbox)):
        await _handle_read_outbox(event)
        return

      # Draft messages
      if isinstance(event, UpdateDraftMessage):
        await _handle_draft_message(event)
        return

      # Dialog pinned/unpinned
      if isinstance(event, UpdateDialogPinned):
        await _handle_dialog_pinned(event)
        return

      # Pinned dialogs reorder
      if isinstance(event, UpdatePinnedDialogs):
        await _handle_pinned_dialogs(event)
        return

      # Chat participants changed
      if isinstance(event, UpdateChatParticipants):
        await _handle_chat_participants(event)
        return

      # Notify settings (mute/unmute)
      if isinstance(event, UpdateNotifySettings):
        await _handle_notify_settings(event)
        return

      # Typing indicators
      if isinstance(event, UpdateUserTyping):
        await _handle_typing(str(event.user_id), str(event.user_id), event)
        return
      if isinstance(event, UpdateChatUserTyping):
        chat_id = str(event.chat_id)
        from_id = str(getattr(event, "from_id", None) or "")
        if hasattr(event, "from_id") and event.from_id:
          from_id = build_peer_id(event.from_id)
        await _handle_typing(chat_id, from_id, event)
        return
      if isinstance(event, UpdateChannelUserTyping):
        chat_id = str(event.channel_id)
        from_id = build_peer_id(event.from_id) if event.from_id else ""
        await _handle_typing(chat_id, from_id, event)
        return

      # Channel metadata update
      if isinstance(event, UpdateChannel):
        await _handle_channel_update(event)
        return

      # Pinned messages
      if isinstance(event, (UpdatePinnedMessages, UpdatePinnedChannelMessages)):
        await _handle_pinned_messages(event)
        return

      # Message deletions (complements high-level handler)
      if isinstance(event, UpdateDeleteMessages):
        await _handle_delete_messages(event)
        return
      if isinstance(event, UpdateDeleteChannelMessages):
        await _handle_delete_channel_messages(event)
        return

      # Folder peers (archive/unarchive)
      if isinstance(event, UpdateFolderPeers):
        await _handle_folder_peers(event)
        return

      # Message content read (e.g. voice messages, self-destruct)
      if isinstance(event, (UpdateReadMessagesContents, UpdateChannelReadMessagesContents)):
        await _handle_read_contents(event)
        return

    except Exception:
      # Raw handler should never crash the client
      pass


# ---------------------------------------------------------------------------
# Individual handlers
# ---------------------------------------------------------------------------


async def _handle_user_status(event: UpdateUserStatus) -> None:
  user_id = str(event.user_id)
  status_name = type(event.status).__name__ if event.status else "unknown"
  try:
    db = await get_db()
    await insert_event(
      db,
      "user_status",
      None,
      {
        "user_id": user_id,
        "status": status_name,
      },
    )
  except Exception:
    pass  # Non-critical


async def _handle_read_inbox(event: Any) -> None:
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
      unread = getattr(event, "still_unread_count", 0)
      store.update_chat(chat_id, {"unread_count": unread})

    try:
      db = await get_db()
      await insert_event(
        db,
        "messages_read",
        chat_id,
        {
          "max_id": max_id,
          "direction": "inbox",
        },
      )
    except Exception:
      pass


async def _handle_read_outbox(event: Any) -> None:
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
      await insert_event(
        db,
        "messages_read",
        chat_id,
        {
          "max_id": max_id,
          "direction": "outbox",
        },
      )
    except Exception:
      pass


async def _handle_draft_message(event: UpdateDraftMessage) -> None:
  peer = getattr(event, "peer", None)
  if not peer:
    return
  chat_id = build_peer_id(peer)
  if not chat_id:
    return

  draft = getattr(event, "draft", None)
  draft_text: str | None = None
  if isinstance(draft, DraftMessage):
    draft_text = draft.message or ""
  elif isinstance(draft, DraftMessageEmpty):
    draft_text = None

  store.update_chat_draft(chat_id, draft_text)

  try:
    db = await get_db()
    await insert_event(
      db,
      "draft_update",
      chat_id,
      {
        "draft": draft_text,
      },
    )
  except Exception:
    pass


async def _handle_dialog_pinned(event: UpdateDialogPinned) -> None:
  peer = getattr(event, "peer", None)
  if not peer:
    return

  # Extract chat_id from DialogPeer
  chat_id = build_peer_id(peer.peer) if isinstance(peer, DialogPeer) else build_peer_id(peer)

  if not chat_id:
    return

  pinned = bool(getattr(event, "pinned", False))
  store.set_chat_pinned(chat_id, pinned)

  try:
    db = await get_db()
    await insert_event(
      db,
      "dialog_pinned",
      chat_id,
      {
        "pinned": pinned,
      },
    )
  except Exception:
    pass


async def _handle_pinned_dialogs(event: UpdatePinnedDialogs) -> None:
  order = getattr(event, "order", None) or []
  pinned_ids: list[str] = []
  for peer in order:
    cid = build_peer_id(peer.peer) if isinstance(peer, DialogPeer) else build_peer_id(peer)
    if cid:
      pinned_ids.append(cid)

  if pinned_ids:
    store.reorder_pinned_chats(pinned_ids)

  try:
    db = await get_db()
    await insert_event(
      db,
      "pinned_dialogs_reorder",
      None,
      {
        "pinned_ids": pinned_ids,
      },
    )
  except Exception:
    pass


async def _handle_chat_participants(event: UpdateChatParticipants) -> None:
  participants = getattr(event, "participants", None)
  if not participants:
    return

  chat_id = str(getattr(participants, "chat_id", ""))
  if not chat_id:
    return

  participant_list = getattr(participants, "participants", []) or []
  count = len(participant_list)
  if count > 0:
    store.update_chat(chat_id, {"participants_count": count})

  try:
    db = await get_db()
    await insert_event(
      db,
      "participants_update",
      chat_id,
      {
        "count": count,
      },
    )
  except Exception:
    pass


async def _handle_notify_settings(event: UpdateNotifySettings) -> None:
  peer = getattr(event, "peer", None)
  if not isinstance(peer, NotifyPeer):
    return

  chat_id = build_peer_id(peer.peer)
  if not chat_id:
    return

  settings = getattr(event, "notify_settings", None)
  if settings is None:
    return

  # Check mute_until — if set and > 0, chat is muted
  mute_until = getattr(settings, "mute_until", None)
  is_muted = mute_until is not None and mute_until > 0

  store.update_chat(chat_id, {"is_muted": is_muted})

  try:
    db = await get_db()
    await insert_event(
      db,
      "notify_settings",
      chat_id,
      {
        "is_muted": is_muted,
        "mute_until": mute_until,
      },
    )
  except Exception:
    pass


async def _handle_typing(chat_id: str, from_id: str, event: Any) -> None:
  action_name = ""
  action = getattr(event, "action", None)
  if action:
    action_name = type(action).__name__

  try:
    db = await get_db()
    await insert_event(
      db,
      "typing",
      chat_id or None,
      {
        "from_id": from_id,
        "action": action_name,
      },
    )
  except Exception:
    pass


async def _handle_channel_update(event: UpdateChannel) -> None:
  channel_id = str(event.channel_id)
  log.debug("Channel metadata update: %s", channel_id)

  try:
    db = await get_db()
    await insert_event(db, "channel_update", channel_id, {})
  except Exception:
    pass


async def _handle_pinned_messages(event: Any) -> None:
  chat_id = ""
  if isinstance(event, UpdatePinnedMessages):
    peer = getattr(event, "peer", None)
    if peer:
      chat_id = build_peer_id(peer)
  elif isinstance(event, UpdatePinnedChannelMessages):
    chat_id = str(event.channel_id)

  pinned = bool(getattr(event, "pinned", False))
  msg_ids = [str(m) for m in (getattr(event, "messages", []) or [])]

  try:
    db = await get_db()
    await insert_event(
      db,
      "pinned_messages",
      chat_id or None,
      {
        "message_ids": msg_ids,
        "pinned": pinned,
      },
    )
  except Exception:
    pass


async def _handle_delete_messages(event: UpdateDeleteMessages) -> None:
  msg_ids = [str(m) for m in (getattr(event, "messages", []) or [])]
  if not msg_ids:
    return

  try:
    db = await get_db()
    await insert_event(
      db,
      "messages_deleted_raw",
      None,
      {
        "message_ids": msg_ids,
      },
    )
  except Exception:
    pass


async def _handle_delete_channel_messages(event: UpdateDeleteChannelMessages) -> None:
  channel_id = str(event.channel_id)
  msg_ids = [str(m) for m in (getattr(event, "messages", []) or [])]
  if not msg_ids:
    return

  # Also update in-memory store
  store.delete_messages(channel_id, msg_ids)

  try:
    db = await get_db()
    await insert_event(
      db,
      "messages_deleted_raw",
      channel_id,
      {
        "message_ids": msg_ids,
      },
    )
  except Exception:
    pass


async def _handle_folder_peers(event: UpdateFolderPeers) -> None:
  folder_peers = getattr(event, "folder_peers", []) or []
  for fp in folder_peers:
    peer = getattr(fp, "peer", None)
    folder_id = getattr(fp, "folder_id", 0)
    if not peer:
      continue
    chat_id = build_peer_id(peer)
    if not chat_id:
      continue

    is_archived = folder_id == 1
    store.update_chat(chat_id, {"is_archived": is_archived})

    try:
      db = await get_db()
      await insert_event(
        db,
        "folder_update",
        chat_id,
        {
          "folder_id": folder_id,
          "is_archived": is_archived,
        },
      )
    except Exception:
      pass


async def _handle_read_contents(event: Any) -> None:
  msg_ids: list[str] = []
  chat_id = ""

  if isinstance(event, UpdateReadMessagesContents):
    msg_ids = [str(m) for m in (getattr(event, "messages", []) or [])]
  elif isinstance(event, UpdateChannelReadMessagesContents):
    chat_id = str(event.channel_id)
    msg_ids = [str(m) for m in (getattr(event, "messages", []) or [])]

  if msg_ids:
    try:
      db = await get_db()
      await insert_event(
        db,
        "content_read",
        chat_id or None,
        {
          "message_ids": msg_ids,
        },
      )
    except Exception:
      pass
