"""
Message get functions — retrieve messages and drafts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from telethon.tl.functions.messages import GetAllDraftsRequest, GetHistoryRequest
from telethon.tl.types import Message

from ...client.builders import build_message
from ...client.telethon_client import get_client
from ...helpers import enforce_rate_limit
from ...state import store
from ..types import ApiResult

if TYPE_CHECKING:
  from ...state.types import TelegramMessage

log = logging.getLogger("skill.telegram.api.message_api.get")


async def get_messages(
  chat_id: str | int,
  limit: int = 20,
  offset: int = 0,
) -> ApiResult[list[TelegramMessage]]:
  """Get messages from a chat (cache-first)."""
  try:
    cached = store.get_cached_messages(str(chat_id), limit, offset)
    if cached:
      log.debug("Returning %d cached messages for chat %s", len(cached), chat_id)
      return ApiResult(data=cached, from_cache=True)

    await enforce_rate_limit("api_read")

    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_input_entity(chat_id)

    result = await mtproto.with_flood_wait_handling(
      lambda: client(
        GetHistoryRequest(
          peer=entity,
          limit=limit,
          offset_id=offset,
          offset_date=0,
          add_offset=0,
          max_id=0,
          min_id=0,
          hash=0,
        )
      )
    )

    if not result or not hasattr(result, "messages"):
      return ApiResult(data=[], from_cache=False)

    messages: list[TelegramMessage] = []
    for msg in result.messages:
      if isinstance(msg, Message):
        built = build_message(msg, str(chat_id))
        if built:
          messages.append(built)

    store.add_messages(str(chat_id), messages)
    log.debug("Fetched %d messages from chat %s", len(messages), chat_id)
    return ApiResult(data=messages, from_cache=False)
  except Exception:
    log.exception("Error fetching messages for chat %s", chat_id)
    return ApiResult(data=[], from_cache=False)


async def get_drafts() -> ApiResult[list[Any]]:
  """Get all drafts."""
  try:
    await enforce_rate_limit("api_read")

    mtproto = get_client()
    client = mtproto.get_client()

    result = await mtproto.with_flood_wait_handling(lambda: client(GetAllDraftsRequest()))

    updates = getattr(result, "updates", [])
    log.debug("Fetched all drafts")
    return ApiResult(data=updates, from_cache=False)
  except Exception:
    log.exception("Error fetching drafts")
    return ApiResult(data=[], from_cache=False)
