"""
Entity builders — convert Telethon objects to typed state objects.

Ported from mtproto/builders.ts. Telethon entities are different from
GramJS entities but the conversion pattern is the same.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from telethon.tl.types import (
  Channel,
  Chat,
  ChatForbidden,
  Message,
  PeerChannel,
  PeerChat,
  PeerUser,
)

from ..state.types import TelegramChat, TelegramMessage, TelegramUser

log = logging.getLogger("skill.telegram.builders")


# ---------------------------------------------------------------------------
# Peer ID helpers
# ---------------------------------------------------------------------------


def build_peer_id(peer: Any) -> str:
  """Extract a string ID from a Telethon peer object."""
  if peer is None:
    return ""
  if isinstance(peer, PeerUser):
    return str(peer.user_id)
  if isinstance(peer, PeerChat):
    return str(peer.chat_id)
  if isinstance(peer, PeerChannel):
    return str(peer.channel_id)
  # Fallback: raw int ID
  if hasattr(peer, "user_id"):
    return str(peer.user_id)
  if hasattr(peer, "chat_id"):
    return str(peer.chat_id)
  if hasattr(peer, "channel_id"):
    return str(peer.channel_id)
  return ""


def get_chat_type(entity: Any) -> Literal["private", "group", "supergroup", "channel"]:
  """Determine chat type from a Telethon entity."""
  if entity is None:
    return "private"
  if isinstance(entity, Channel):
    return "supergroup" if entity.megagroup else "channel"
  if isinstance(entity, (Chat, ChatForbidden)):
    return "group"
  return "private"


# ---------------------------------------------------------------------------
# Chat builder
# ---------------------------------------------------------------------------


def build_chat(
  dialog_or_entity: Any,
  entity: Any = None,
  last_msg: TelegramMessage | None = None,
) -> TelegramChat:
  """Build a TelegramChat from a Telethon Dialog or entity."""
  if entity is None:
    entity = dialog_or_entity

  # Determine ID
  if hasattr(dialog_or_entity, "peer"):
    chat_id = build_peer_id(dialog_or_entity.peer)
  elif hasattr(entity, "id"):
    chat_id = str(entity.id)
  else:
    chat_id = ""

  chat_type = get_chat_type(entity)

  # Build title
  if chat_type == "private":
    first = getattr(entity, "first_name", "") or ""
    last = getattr(entity, "last_name", "") or ""
    title = " ".join(p for p in [first, last] if p) or f"User {chat_id}"
  else:
    title = getattr(entity, "title", None) or f"Chat {chat_id}"

  chat = TelegramChat(
    id=chat_id,
    type=chat_type,
    title=title,
    unread_count=getattr(dialog_or_entity, "unread_count", 0) or 0,
    is_pinned=bool(getattr(dialog_or_entity, "pinned", False)),
  )

  if hasattr(entity, "username") and entity.username:
    chat.username = entity.username
  if hasattr(entity, "access_hash") and entity.access_hash is not None:
    chat.access_hash = str(entity.access_hash)
  if hasattr(entity, "participants_count") and entity.participants_count is not None:
    chat.participants_count = entity.participants_count

  if last_msg:
    chat.last_message = last_msg
    chat.last_message_date = last_msg.date

  return chat


# ---------------------------------------------------------------------------
# Message builder
# ---------------------------------------------------------------------------


def build_message(msg: Any, fallback_chat_id: str = "") -> TelegramMessage | None:
  """Build a TelegramMessage from a Telethon Message."""
  if msg is None or not isinstance(msg, Message):
    return None
  if msg.id is None:
    return None

  chat_id = fallback_chat_id
  if msg.peer_id:
    chat_id = build_peer_id(msg.peer_id) or chat_id

  telegram_msg = TelegramMessage(
    id=str(msg.id),
    chat_id=chat_id,
    date=msg.date.timestamp() if msg.date else 0,
    message=msg.message or "",
    is_outgoing=bool(msg.out),
    is_edited=msg.edit_date is not None,
    is_forwarded=msg.fwd_from is not None,
  )

  if msg.from_id:
    telegram_msg.from_id = build_peer_id(msg.from_id)

  if msg.reply_to:
    if hasattr(msg.reply_to, "reply_to_msg_id") and msg.reply_to.reply_to_msg_id:
      telegram_msg.reply_to_message_id = str(msg.reply_to.reply_to_msg_id)
    if hasattr(msg.reply_to, "reply_to_top_id") and msg.reply_to.reply_to_top_id:
      telegram_msg.thread_id = str(msg.reply_to.reply_to_top_id)

  if msg.media:
    media_type = type(msg.media).__name__
    if media_type != "MessageMediaEmpty":
      telegram_msg.media = {"type": media_type}

  if msg.views is not None:
    telegram_msg.views = msg.views

  return telegram_msg


# ---------------------------------------------------------------------------
# User builder
# ---------------------------------------------------------------------------


def build_user(user: Any) -> TelegramUser:
  """Build a TelegramUser from a Telethon User object."""
  if user is None or not hasattr(user, "id"):
    return TelegramUser(id="0", first_name="Unknown")

  return TelegramUser(
    id=str(user.id),
    first_name=getattr(user, "first_name", "") or "",
    last_name=getattr(user, "last_name", None),
    username=getattr(user, "username", None),
    phone_number=getattr(user, "phone", None),
    is_bot=bool(getattr(user, "bot", False)),
    is_verified=True if getattr(user, "verified", False) else None,
    is_premium=True if getattr(user, "premium", False) else None,
    access_hash=str(user.access_hash) if getattr(user, "access_hash", None) is not None else None,
  )


# ---------------------------------------------------------------------------
# Entity map builder
# ---------------------------------------------------------------------------


def build_entity_map(result: Any) -> dict[str, Any]:
  """Build a map of entity ID -> raw entity from a Telethon result."""
  entity_map: dict[str, Any] = {}

  users = getattr(result, "users", []) or []
  chats = getattr(result, "chats", []) or []

  for u in users:
    if hasattr(u, "id"):
      entity_map[str(u.id)] = u

  for c in chats:
    if hasattr(c, "id"):
      entity_map[str(c.id)] = c

  return entity_map


# ---------------------------------------------------------------------------
# Channel pts extraction
# ---------------------------------------------------------------------------


def extract_channel_pts_from_dialogs(dialogs: Any) -> dict[str, int]:
  """Extract channel pts from raw GetDialogs result for sync tracking.

  The dialogs result contains Dialog objects with a pts field for channels.
  Returns a dict mapping channel_id -> pts.
  """
  channel_pts: dict[str, int] = {}

  raw_dialogs = getattr(dialogs, "dialogs", []) or []
  for d in raw_dialogs:
    pts = getattr(d, "pts", None)
    if pts is None:
      continue
    peer = getattr(d, "peer", None)
    if peer is None:
      continue
    if isinstance(peer, PeerChannel):
      channel_pts[str(peer.channel_id)] = pts

  return channel_pts
