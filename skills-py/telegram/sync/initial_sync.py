"""
Initial dialog loading — Telegram Web A-style full sync on auth.

Sequence:
  1. Mark syncing state
  2. Fetch global update state (pts/qts/date/seq)
  3. Load pinned dialogs
  4. Load first batch of dialogs (100)
  5. Push to store + DB → UI can show chats
  6. Background: paginate remaining dialogs, load archived, preload messages
  7. catch_up() for missed updates
  8. Mark initial sync complete
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from telethon.tl.functions.messages import (
  GetDialogsRequest,
  GetHistoryRequest,
  GetPinnedDialogsRequest,
)
from telethon.tl.functions.updates import GetStateRequest
from telethon.tl.types import InputPeerEmpty

from ..client.builders import (
  build_chat,
  build_entity_map,
  build_message,
  build_user,
  extract_channel_pts_from_dialogs,
)
from ..db.connection import get_db
from ..db.queries import upsert_chats_batch, upsert_messages_batch, upsert_users_batch
from ..state import store
from .update_state import save_channel_pts_batch, save_update_state

if TYPE_CHECKING:
  from telethon import TelegramClient

  from ..state.types import TelegramChat, TelegramMessage, TelegramUser

log = logging.getLogger("skill.telegram.sync.initial_sync")

# Matching Telegram Web A constants
DIALOG_BATCH_SIZE = 100
MESSAGE_PRELOAD_LIMIT = 60
TOP_CHATS_TO_PRELOAD = 20
PRELOAD_DELAY_MS = 100
MAX_DIALOG_BATCHES = 100


async def run_initial_sync(
  client: TelegramClient,
  upsert_entity_fn: Any = None,
  upsert_relationship_fn: Any = None,
) -> None:
  """Run the full initial sync sequence."""
  log.info("Starting initial sync")
  store.set_sync_status(is_syncing=True)

  try:
    # 1. Fetch global update state
    await _fetch_and_save_update_state(client)

    # 2. Load pinned dialogs
    pinned_chats, pinned_users, pinned_messages = await _load_pinned_dialogs(client)

    # 3. Load first batch of dialogs
    (
      first_chats,
      first_users,
      first_messages,
      first_channel_pts,
      has_more,
    ) = await _load_dialog_batch(client, offset_date=0, offset_id=0, offset_peer=InputPeerEmpty())

    # Merge pinned into first batch (pinned first)
    all_chats = {**{c.id: c for c in first_chats}, **{c.id: c for c in pinned_chats}}
    all_users = {**first_users, **pinned_users}
    all_messages = pinned_messages + first_messages
    pinned_ids = [c.id for c in pinned_chats]
    first_ids = [c.id for c in first_chats if c.id not in set(pinned_ids)]
    chats_order = pinned_ids + first_ids

    # 4. Push to store — UI can now render chats
    store.replace_chats(all_chats, chats_order)
    store.add_users(all_users)
    for msg in all_messages:
      store.add_messages(msg.chat_id, [msg])
    store.set_sync_status(is_synced=True)

    log.info(
      "First batch loaded: %d chats, %d users, %d messages",
      len(all_chats),
      len(all_users),
      len(all_messages),
    )

    # 5. Persist to SQLite
    await _persist_batch(list(all_chats.values()), all_users, all_messages)
    await save_channel_pts_batch(first_channel_pts)

    # 6. Emit initial entities
    if upsert_entity_fn and upsert_relationship_fn:
      try:
        from ..entities import emit_initial_entities

        await emit_initial_entities(upsert_entity_fn, upsert_relationship_fn)
      except Exception:
        log.exception("Failed to emit initial entities during sync")

    # 7. Background: load remaining dialogs + preload messages
    await _load_remaining_dialogs(client, has_more, first_chats, first_channel_pts)

    # 8. Load archived dialogs
    await _load_archived_dialogs(client)

    # 9. Preload messages for top chats
    await _preload_top_chat_messages(client)

    # 10. Catch up on any missed updates
    try:
      await client.catch_up()
      log.info("catch_up() completed")
    except Exception:
      log.debug("catch_up() failed (non-critical)", exc_info=True)

    # 11. Mark complete
    store.set_initial_sync_complete(True)
    store.set_sync_status(is_syncing=False)
    log.info("Initial sync complete")

  except Exception:
    log.exception("Initial sync failed")
    store.set_sync_status(is_syncing=False)


async def _fetch_and_save_update_state(client: TelegramClient) -> None:
  """Fetch current update state from Telegram and persist."""
  try:
    state = await client(GetStateRequest())
    date_val = state.date
    if hasattr(date_val, "timestamp"):
      date_val = int(date_val.timestamp())
    await save_update_state(state.pts, state.qts, int(date_val), state.seq)
    log.info(
      "Update state: pts=%d qts=%d date=%d seq=%d",
      state.pts,
      state.qts,
      int(date_val),
      state.seq,
    )
  except Exception:
    log.exception("Failed to fetch update state")


async def _load_pinned_dialogs(
  client: TelegramClient,
) -> tuple[list[TelegramChat], dict[str, TelegramUser], list[TelegramMessage]]:
  """Load pinned dialogs via GetPinnedDialogsRequest."""
  chats: list[TelegramChat] = []
  users: dict[str, TelegramUser] = {}
  messages: list[TelegramMessage] = []

  try:
    result = await client(GetPinnedDialogsRequest(folder_id=0))
    entity_map = build_entity_map(result)

    # Build message lookup
    msg_map: dict[str, TelegramMessage] = {}
    for raw_msg in getattr(result, "messages", []) or []:
      built = build_message(raw_msg)
      if built:
        msg_map[built.id] = built
        messages.append(built)

    # Build users
    for raw_user in getattr(result, "users", []) or []:
      built_user = build_user(raw_user)
      if built_user.id != "0":
        users[built_user.id] = built_user

    # Build chats from dialogs
    for dialog in getattr(result, "dialogs", []) or []:
      peer = getattr(dialog, "peer", None)
      if not peer:
        continue
      from ..client.builders import build_peer_id

      peer_id = build_peer_id(peer)
      entity = entity_map.get(peer_id)

      # Find top message for this dialog
      top_msg_id = str(getattr(dialog, "top_message", 0))
      last_msg = msg_map.get(top_msg_id)

      chat = build_chat(dialog, entity, last_msg)
      chat.is_pinned = True
      chats.append(chat)

    log.info("Loaded %d pinned dialogs", len(chats))
  except Exception:
    log.exception("Failed to load pinned dialogs")

  return chats, users, messages


async def _load_dialog_batch(
  client: TelegramClient,
  offset_date: int | float,
  offset_id: int,
  offset_peer: Any,
) -> tuple[
  list[TelegramChat], dict[str, TelegramUser], list[TelegramMessage], dict[str, int], bool
]:
  """Load a single batch of dialogs."""
  chats: list[TelegramChat] = []
  users: dict[str, TelegramUser] = {}
  messages: list[TelegramMessage] = []

  result = await client(
    GetDialogsRequest(
      offset_date=int(offset_date),
      offset_id=offset_id,
      offset_peer=offset_peer,
      limit=DIALOG_BATCH_SIZE,
      hash=0,
    )
  )

  entity_map = build_entity_map(result)
  channel_pts = extract_channel_pts_from_dialogs(result)

  # Build message lookup
  msg_map: dict[str, TelegramMessage] = {}
  for raw_msg in getattr(result, "messages", []) or []:
    built = build_message(raw_msg)
    if built:
      msg_map[built.id] = built
      messages.append(built)

  # Build users
  for raw_user in getattr(result, "users", []) or []:
    built_user = build_user(raw_user)
    if built_user.id != "0":
      users[built_user.id] = built_user

  # Build chats from dialogs
  raw_dialogs = getattr(result, "dialogs", []) or []
  for dialog in raw_dialogs:
    peer = getattr(dialog, "peer", None)
    if not peer:
      continue
    from ..client.builders import build_peer_id

    peer_id = build_peer_id(peer)
    entity = entity_map.get(peer_id)

    top_msg_id = str(getattr(dialog, "top_message", 0))
    last_msg = msg_map.get(top_msg_id)

    chat = build_chat(dialog, entity, last_msg)
    chats.append(chat)

  has_more = len(raw_dialogs) >= DIALOG_BATCH_SIZE
  return chats, users, messages, channel_pts, has_more


async def _load_remaining_dialogs(
  client: TelegramClient,
  has_more: bool,
  first_batch_chats: list[TelegramChat],
  all_channel_pts: dict[str, int],
) -> None:
  """Paginate through all remaining dialogs in the background."""
  if not has_more:
    return

  batch_num = 1
  last_chats = first_batch_chats

  while has_more and batch_num < MAX_DIALOG_BATCHES:
    # Compute offset from last chat in previous batch
    if not last_chats:
      break

    last_chat = last_chats[-1]
    offset_date = int(last_chat.last_message_date or 0)
    offset_id = int(last_chat.last_message.id) if last_chat.last_message else 0

    # Get input peer for offset
    try:
      offset_peer = await client.get_input_entity(int(last_chat.id))
    except Exception:
      offset_peer = InputPeerEmpty()

    try:
      (
        batch_chats,
        batch_users,
        batch_messages,
        batch_channel_pts,
        has_more,
      ) = await _load_dialog_batch(client, offset_date, offset_id, offset_peer)
    except Exception:
      log.exception("Failed to load dialog batch %d", batch_num + 1)
      break

    if not batch_chats:
      break

    # Update store incrementally
    store.add_chats(batch_chats)
    store.add_users(batch_users)
    for msg in batch_messages:
      store.add_messages(msg.chat_id, [msg])

    # Persist
    await _persist_batch(batch_chats, batch_users, batch_messages)

    all_channel_pts.update(batch_channel_pts)
    await save_channel_pts_batch(batch_channel_pts)

    last_chats = batch_chats
    batch_num += 1
    log.info("Dialog batch %d: %d chats loaded", batch_num, len(batch_chats))

  log.info("Finished loading dialogs: %d batches total", batch_num)


async def _load_archived_dialogs(client: TelegramClient) -> None:
  """Load archived dialogs (folder_id=1) with same pagination."""
  try:
    offset_date = 0
    offset_id = 0
    offset_peer = InputPeerEmpty()
    batch_num = 0

    while batch_num < MAX_DIALOG_BATCHES:
      result = await client(
        GetDialogsRequest(
          offset_date=offset_date,
          offset_id=offset_id,
          offset_peer=offset_peer,
          limit=DIALOG_BATCH_SIZE,
          hash=0,
          folder_id=1,
        )
      )

      entity_map = build_entity_map(result)
      raw_dialogs = getattr(result, "dialogs", []) or []
      if not raw_dialogs:
        break

      chats: list[TelegramChat] = []
      users: dict[str, TelegramUser] = {}
      messages: list[TelegramMessage] = []

      # Build message lookup
      msg_map: dict[str, TelegramMessage] = {}
      for raw_msg in getattr(result, "messages", []) or []:
        built = build_message(raw_msg)
        if built:
          msg_map[built.id] = built
          messages.append(built)

      for raw_user in getattr(result, "users", []) or []:
        built_user = build_user(raw_user)
        if built_user.id != "0":
          users[built_user.id] = built_user

      for dialog in raw_dialogs:
        peer = getattr(dialog, "peer", None)
        if not peer:
          continue
        from ..client.builders import build_peer_id

        peer_id = build_peer_id(peer)
        entity = entity_map.get(peer_id)

        top_msg_id = str(getattr(dialog, "top_message", 0))
        last_msg = msg_map.get(top_msg_id)

        chat = build_chat(dialog, entity, last_msg)
        chat.is_archived = True
        chats.append(chat)

      store.add_chats(chats)
      store.add_users(users)
      for msg in messages:
        store.add_messages(msg.chat_id, [msg])

      await _persist_batch(chats, users, messages)

      if len(raw_dialogs) < DIALOG_BATCH_SIZE:
        break

      last_chat = chats[-1] if chats else None
      if last_chat:
        offset_date = int(last_chat.last_message_date or 0)
        offset_id = int(last_chat.last_message.id) if last_chat.last_message else 0
        try:
          offset_peer = await client.get_input_entity(int(last_chat.id))
        except Exception:
          break
      else:
        break

      batch_num += 1

    log.info("Loaded archived dialogs (%d batches)", batch_num + 1)
  except Exception:
    log.exception("Failed to load archived dialogs")


async def _preload_top_chat_messages(client: TelegramClient) -> None:
  """Preload messages for the top N chats."""
  ordered = store.get_ordered_chats(TOP_CHATS_TO_PRELOAD)
  loaded = 0

  for chat in ordered:
    try:
      input_peer = await client.get_input_entity(int(chat.id))
      result = await client(
        GetHistoryRequest(
          peer=input_peer,
          offset_id=0,
          offset_date=0,
          add_offset=0,
          limit=MESSAGE_PRELOAD_LIMIT,
          max_id=0,
          min_id=0,
          hash=0,
        )
      )

      entity_map = build_entity_map(result)
      messages: list[TelegramMessage] = []
      users: dict[str, TelegramUser] = {}

      for raw_msg in getattr(result, "messages", []) or []:
        built = build_message(raw_msg, fallback_chat_id=chat.id)
        if built:
          # Resolve sender name
          if built.from_id:
            raw_entity = entity_map.get(built.from_id)
            if raw_entity:
              name = getattr(raw_entity, "first_name", "") or ""
              built.from_name = name
          messages.append(built)

      for raw_user in getattr(result, "users", []) or []:
        built_user = build_user(raw_user)
        if built_user.id != "0":
          users[built_user.id] = built_user

      if messages:
        store.add_messages(chat.id, messages)
      if users:
        store.add_users(users)

      # Persist
      try:
        db = await get_db()
        if messages:
          await upsert_messages_batch(db, messages)
        if users:
          await upsert_users_batch(db, list(users.values()))
      except Exception:
        log.debug("Failed to persist preloaded messages for %s", chat.id)

      loaded += 1
      await asyncio.sleep(PRELOAD_DELAY_MS / 1000.0)

    except Exception:
      log.debug("Failed to preload messages for chat %s", chat.id, exc_info=True)

  log.info("Preloaded messages for %d/%d top chats", loaded, len(ordered))


async def _persist_batch(
  chats: list[TelegramChat],
  users: dict[str, TelegramUser],
  messages: list[TelegramMessage],
) -> None:
  """Persist a batch of chats, users, messages to SQLite."""
  try:
    db = await get_db()
    if chats:
      await upsert_chats_batch(db, chats)
    if users:
      await upsert_users_batch(db, list(users.values()))
    if messages:
      await upsert_messages_batch(db, messages)
  except Exception:
    log.exception("Failed to persist sync batch")
