"""
Message list functions — list topics and other message-related lists.
"""

from __future__ import annotations

import logging
from typing import Any

from telethon.tl.types import InputChannel

from ...client.telethon_client import get_client
from ...helpers import enforce_rate_limit

try:
  from telethon.tl.functions.channels import GetForumTopicsRequest
except ImportError:
  GetForumTopicsRequest = None  # Not available in telethon < 1.43

from ..types import ApiResult

log = logging.getLogger("skill.telegram.api.message_api.list")


async def list_topics(chat_id: str) -> ApiResult[list[Any]]:
  """List topics in a forum/supergroup."""
  try:
    await enforce_rate_limit("api_read")

    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_input_entity(chat_id)

    if not isinstance(entity, InputChannel):
      log.debug("Chat %s is not a channel/supergroup", chat_id)
      return ApiResult(data=[], from_cache=False)

    if GetForumTopicsRequest is None:
      log.debug("GetForumTopicsRequest not available in this telethon version")
      return ApiResult(data=[], from_cache=False)

    result = await mtproto.with_flood_wait_handling(
      lambda: client(
        GetForumTopicsRequest(
          channel=entity,
          offset_date=0,
          offset_id=0,
          offset_topic=0,
          limit=100,
        )
      )
    )

    topics = getattr(result, "topics", [])
    log.debug("Fetched %d topics from chat %s", len(topics), chat_id)
    return ApiResult(data=topics, from_cache=False)
  except Exception:
    log.exception("Error fetching topics from chat %s", chat_id)
    return ApiResult(data=[], from_cache=False)
