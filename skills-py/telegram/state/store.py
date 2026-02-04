"""
In-process state store for the Telegram runtime skill.

Ported from state/store.ts. Uses plain dict-based state.
State mutations are synchronous. After each mutation, listeners are notified.
"""

from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING

from .types import (
  TelegramAuthStatus,
  TelegramChat,
  TelegramConnectionStatus,
  TelegramMessage,
  TelegramState,
  TelegramThread,
  TelegramUser,
  initial_state,
)

if TYPE_CHECKING:
  from collections.abc import Callable

_state: TelegramState = initial_state()
_listeners: list[Callable[[], None]] = []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_state() -> TelegramState:
  return _state


def subscribe(listener: Callable[[], None]) -> Callable[[], None]:
  _listeners.append(listener)

  def unsubscribe() -> None:
    with contextlib.suppress(ValueError):
      _listeners.remove(listener)

  return unsubscribe


def _notify() -> None:
  for fn in _listeners:
    fn()


# ---------------------------------------------------------------------------
# Connection / Auth
# ---------------------------------------------------------------------------


def set_connection_status(status: TelegramConnectionStatus) -> None:
  global _state
  _state = _state.model_copy(update={"connection_status": status})
  if status != "error":
    _state = _state.model_copy(update={"connection_error": None})
  _notify()


def set_connection_error(error: str | None) -> None:
  global _state
  updates: dict = {"connection_error": error}
  if error:
    updates["connection_status"] = "error"
  _state = _state.model_copy(update=updates)
  _notify()


def set_auth_status(status: TelegramAuthStatus) -> None:
  global _state
  _state = _state.model_copy(update={"auth_status": status})
  if status != "error":
    _state = _state.model_copy(update={"auth_error": None})
  _notify()


def set_auth_error(error: str | None) -> None:
  global _state
  updates: dict = {"auth_error": error}
  if error:
    updates["auth_status"] = "error"
  _state = _state.model_copy(update=updates)
  _notify()


def set_session_string(session_string: str | None) -> None:
  global _state
  _state = _state.model_copy(update={"session_string": session_string})
  _notify()


def set_is_initialized(value: bool) -> None:
  global _state
  _state = _state.model_copy(update={"is_initialized": value})
  _notify()


def set_current_user(user: TelegramUser | None) -> None:
  global _state
  _state = _state.model_copy(update={"current_user": user})
  _notify()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def add_users(users: dict[str, TelegramUser]) -> None:
  global _state
  merged = {**_state.users, **users}
  _state = _state.model_copy(update={"users": merged})
  _notify()


def get_user(user_id: str) -> TelegramUser | None:
  return _state.users.get(user_id)


# ---------------------------------------------------------------------------
# Chats
# ---------------------------------------------------------------------------


def replace_chats(chats: dict[str, TelegramChat], chats_order: list[str]) -> None:
  global _state
  _state = _state.model_copy(update={"chats": chats, "chats_order": chats_order})
  _notify()


def add_chats(
  chats_input: list[TelegramChat] | dict[str, TelegramChat], append_order: list[str] | None = None
) -> None:
  global _state
  if isinstance(chats_input, list):
    chat_record = {c.id: c for c in chats_input}
    order_ids = [c.id for c in chats_input]
  else:
    chat_record = chats_input
    order_ids = append_order or list(chats_input.keys())

  new_chats = {**_state.chats, **chat_record}
  existing = set(_state.chats_order)
  new_order = list(_state.chats_order)
  for cid in order_ids:
    if cid not in existing:
      new_order.append(cid)
      existing.add(cid)

  _state = _state.model_copy(update={"chats": new_chats, "chats_order": new_order})
  _notify()


def add_chat(chat: TelegramChat) -> None:
  global _state
  chats = {**_state.chats, chat.id: chat}
  chats_order = (
    _state.chats_order if chat.id in _state.chats_order else [chat.id, *_state.chats_order]
  )
  _state = _state.model_copy(update={"chats": chats, "chats_order": chats_order})
  _notify()


def update_chat(chat_id: str, updates: dict) -> None:
  global _state
  existing = _state.chats.get(chat_id)
  if not existing:
    return
  updated = existing.model_copy(update=updates)
  _state = _state.model_copy(update={"chats": {**_state.chats, chat_id: updated}})
  _notify()


def get_chat_by_id(chat_id: str | int) -> TelegramChat | None:
  id_str = str(chat_id)
  chat = _state.chats.get(id_str)
  if chat:
    return chat

  if isinstance(chat_id, str) and (
    chat_id.startswith("@") or re.match(r"^[a-zA-Z0-9_]+$", chat_id)
  ):
    username = chat_id if chat_id.startswith("@") else f"@{chat_id}"
    for c in _state.chats.values():
      if c.username and (c.username == username or c.username == username[1:]):
        return c
  return None


def get_ordered_chats(limit: int = 20) -> list[TelegramChat]:
  result = []
  for cid in _state.chats_order:
    chat = _state.chats.get(cid)
    if chat:
      result.append(chat)
    if len(result) >= limit:
      break
  return result


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def add_messages(chat_id: str, messages: list[TelegramMessage]) -> None:
  global _state
  by_id = dict(_state.messages.get(chat_id, {}))
  order = list(_state.messages_order.get(chat_id, []))
  existing = set(order)

  for msg in messages:
    by_id[msg.id] = msg
    if msg.id not in existing:
      order.append(msg.id)
      existing.add(msg.id)

  order.sort(key=lambda mid: by_id[mid].date if mid in by_id else 0)

  new_messages = {**_state.messages, chat_id: by_id}
  new_order = {**_state.messages_order, chat_id: order}
  _state = _state.model_copy(update={"messages": new_messages, "messages_order": new_order})
  _notify()


def get_cached_messages(
  chat_id: str, limit: int = 20, offset: int = 0
) -> list[TelegramMessage] | None:
  order = _state.messages_order.get(chat_id, [])
  by_id = _state.messages.get(chat_id, {})
  all_msgs = [by_id[mid] for mid in order if mid in by_id]
  chunk = all_msgs[offset : offset + limit]
  return chunk if chunk else None


def update_message(chat_id: str, message_id: str, updates: dict) -> None:
  global _state
  msg = (_state.messages.get(chat_id) or {}).get(message_id)
  if not msg:
    return
  updated_msg = msg.model_copy(update=updates)
  chat_msgs = {**_state.messages.get(chat_id, {}), message_id: updated_msg}
  _state = _state.model_copy(update={"messages": {**_state.messages, chat_id: chat_msgs}})
  _notify()


def delete_messages(chat_id: str, message_ids: list[str]) -> None:
  global _state
  to_delete = set(message_ids)
  by_id = {k: v for k, v in (_state.messages.get(chat_id) or {}).items() if k not in to_delete}
  order = [mid for mid in (_state.messages_order.get(chat_id) or []) if mid not in to_delete]
  _state = _state.model_copy(
    update={
      "messages": {**_state.messages, chat_id: by_id},
      "messages_order": {**_state.messages_order, chat_id: order},
    }
  )
  _notify()


# ---------------------------------------------------------------------------
# Threads
# ---------------------------------------------------------------------------


def add_thread(thread: TelegramThread) -> None:
  global _state
  chat_id = thread.chat_id
  chat_threads = {**(_state.threads.get(chat_id) or {}), thread.id: thread}
  chat_order = list(_state.threads_order.get(chat_id) or [])
  if thread.id not in chat_order:
    chat_order.append(thread.id)
  _state = _state.model_copy(
    update={
      "threads": {**_state.threads, chat_id: chat_threads},
      "threads_order": {**_state.threads_order, chat_id: chat_order},
    }
  )
  _notify()


# ---------------------------------------------------------------------------
# Search / Remove
# ---------------------------------------------------------------------------


def remove_chat(chat_id: str) -> None:
  global _state
  chats = {k: v for k, v in _state.chats.items() if k != chat_id}
  chats_order = [cid for cid in _state.chats_order if cid != chat_id]
  _state = _state.model_copy(update={"chats": chats, "chats_order": chats_order})
  _notify()


def remove_message(chat_id: str, message_id: int | str) -> None:
  delete_messages(chat_id, [str(message_id)])


def search_chats_in_cache(query: str) -> list[TelegramChat]:
  q = query.lower()
  return [
    c
    for c in get_ordered_chats(9999)
    if (c.title or "").lower().find(q) >= 0 or (c.username or "").lower().find(q) >= 0
  ]


# ---------------------------------------------------------------------------
# Sync helpers
# ---------------------------------------------------------------------------


def set_sync_status(is_syncing: bool | None = None, is_synced: bool | None = None) -> None:
  global _state
  updates: dict = {}
  if is_syncing is not None:
    updates["is_syncing"] = is_syncing
  if is_synced is not None:
    updates["is_synced"] = is_synced
  _state = _state.model_copy(update=updates)
  _notify()


def set_loading_chats(value: bool) -> None:
  global _state
  _state = _state.model_copy(update={"is_loading_chats": value})
  _notify()


def set_loading_messages(value: bool) -> None:
  global _state
  _state = _state.model_copy(update={"is_loading_messages": value})
  _notify()


def set_initial_sync_complete(value: bool) -> None:
  global _state
  _state = _state.model_copy(update={"initial_sync_complete": value})
  _notify()


def set_sync_pts(pts: int, qts: int, date: int, seq: int) -> None:
  global _state
  _state = _state.model_copy(
    update={
      "sync_pts": pts,
      "sync_qts": qts,
      "sync_date": date,
      "sync_seq": seq,
    }
  )
  _notify()


def update_chat_draft(chat_id: str, draft: str | None) -> None:
  update_chat(chat_id, {"draft_message": draft})


def set_chat_pinned(chat_id: str, pinned: bool) -> None:
  update_chat(chat_id, {"is_pinned": pinned})


def reorder_pinned_chats(pinned_ids: list[str]) -> None:
  """Reorder chats so that pinned_ids appear first in order."""
  global _state
  pinned_set = set(pinned_ids)
  # Mark pinned state
  new_chats = dict(_state.chats)
  for cid, chat in new_chats.items():
    if cid in pinned_set and not chat.is_pinned:
      new_chats[cid] = chat.model_copy(update={"is_pinned": True})
    elif cid not in pinned_set and chat.is_pinned:
      new_chats[cid] = chat.model_copy(update={"is_pinned": False})

  # Reorder: pinned first, then rest in existing order
  rest = [cid for cid in _state.chats_order if cid not in pinned_set]
  new_order = [cid for cid in pinned_ids if cid in new_chats] + rest

  _state = _state.model_copy(update={"chats": new_chats, "chats_order": new_order})
  _notify()


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def reset_state() -> None:
  global _state
  _state = initial_state()
  _notify()
