"""
Search API — Telethon wrappers for search operations.

Ported from api/search-api.ts. Rate limited.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from telethon.tl.functions.contacts import (
  ResolveUsernameRequest,
)
from telethon.tl.functions.contacts import (
  SearchRequest as ContactsSearchRequest,
)
from telethon.tl.functions.messages import (
  SearchGlobalRequest,
)
from telethon.tl.functions.messages import (
  SearchRequest as MessagesSearchRequest,
)
from telethon.tl.types import (
  InputMessagesFilterEmpty,
  InputPeerEmpty,
)
from telethon.tl.types import (
  messages as messages_types,
)

from ..client.builders import build_user
from ..client.telethon_client import get_client
from ..helpers import enforce_rate_limit

log = logging.getLogger("skill.telegram.api.search")

T = TypeVar("T")


@dataclass
class ApiResult(Generic[T]):
  data: T
  from_cache: bool


async def search_public_chats(query: str, limit: int = 20) -> ApiResult[list[Any]]:
  """Search for public chats and users."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    result = await mtproto.invoke(ContactsSearchRequest(q=query, limit=limit))

    results = []
    for chat in result.chats:
      results.append(
        {
          "type": "chat",
          "id": str(chat.id),
          "title": getattr(chat, "title", None),
          "username": getattr(chat, "username", None),
          "participantsCount": getattr(chat, "participants_count", None),
        }
      )

    for user in result.users:
      u = build_user(user)
      results.append(
        {
          "type": "user",
          "id": u.id,
          "username": u.username,
          "firstName": u.first_name,
          "lastName": u.last_name,
        }
      )

    return ApiResult(data=results, from_cache=False)
  except Exception:
    log.exception("Error searching public chats")
    return ApiResult(data=[], from_cache=False)


async def search_messages(
  query: str,
  chat_id: str | None = None,
  limit: int = 20,
) -> ApiResult[list[Any]]:
  """Search messages, optionally within a specific chat."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    client = mtproto.get_client()

    if chat_id:
      entity = await client.get_input_entity(chat_id)
      result = await mtproto.invoke(
        MessagesSearchRequest(
          peer=entity,
          q=query,
          filter=InputMessagesFilterEmpty(),
          min_date=0,
          max_date=0,
          offset_id=0,
          add_offset=0,
          limit=limit,
          max_id=0,
          min_id=0,
          hash=0,
        )
      )
    else:
      result = await mtproto.invoke(
        SearchGlobalRequest(
          q=query,
          filter=InputMessagesFilterEmpty(),
          min_date=0,
          max_date=0,
          offset_rate=0,
          offset_peer=InputPeerEmpty(),
          offset_id=0,
          limit=limit,
        )
      )

    if isinstance(result, (messages_types.Messages, messages_types.MessagesSlice)):
      found = []
      for msg in result.messages:
        found.append(
          {
            "id": msg.id,
            "message": getattr(msg, "message", None),
            "date": getattr(msg, "date", None),
            "fromId": str(msg.from_id) if getattr(msg, "from_id", None) else None,
          }
        )
      return ApiResult(data=found, from_cache=False)

    return ApiResult(data=[], from_cache=False)
  except Exception:
    log.exception("Error searching messages")
    return ApiResult(data=[], from_cache=False)


async def resolve_username(username: str) -> ApiResult[Any | None]:
  """Resolve a username to a user or chat."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    clean_username = username.lstrip("@")

    result = await mtproto.invoke(ResolveUsernameRequest(username=clean_username))

    if result.users:
      u = build_user(result.users[0])
      return ApiResult(data={"type": "user", **u.model_dump()}, from_cache=False)

    if result.chats:
      chat = result.chats[0]
      return ApiResult(
        data={
          "type": "chat",
          "id": str(chat.id),
          "title": getattr(chat, "title", None),
          "username": getattr(chat, "username", None),
        },
        from_cache=False,
      )

    return ApiResult(data=None, from_cache=False)
  except Exception:
    log.exception("Error resolving username")
    return ApiResult(data=None, from_cache=False)
