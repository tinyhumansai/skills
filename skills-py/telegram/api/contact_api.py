"""
Contact API — Telethon wrappers for contact operations.

Ported from api/contact-api.ts. Cache-first pattern with rate limiting.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from telethon.tl.functions.contacts import (
  AddContactRequest,
  BlockRequest,
  DeleteContactsRequest,
  GetBlockedRequest,
  GetContactIDsRequest,
  GetContactsRequest,
  ImportContactsRequest,
  UnblockRequest,
)
from telethon.tl.functions.contacts import (
  SearchRequest as ContactsSearchRequest,
)
from telethon.tl.types import (
  InputPeerUser,
  InputPhoneContact,
  InputUser,
  contacts,
)

from ..client.builders import build_user
from ..client.telethon_client import get_client
from ..helpers import enforce_rate_limit
from ..state import store

if TYPE_CHECKING:
  from ..state.types import TelegramMessage, TelegramUser

log = logging.getLogger("skill.telegram.api.contact")

T = TypeVar("T")


@dataclass
class ApiResult(Generic[T]):
  data: T
  from_cache: bool


async def list_contacts(limit: int = 20) -> ApiResult[list[TelegramUser]]:
  """List user's contacts."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    mtproto.get_client()
    result = await mtproto.invoke(GetContactsRequest(hash=0))

    if not isinstance(result, contacts.Contacts):
      return ApiResult(data=[], from_cache=False)

    users = [build_user(u) for u in result.users[:limit]]
    return ApiResult(data=users, from_cache=False)
  except Exception:
    log.exception("Error listing contacts")
    return ApiResult(data=[], from_cache=False)


async def search_contacts(query: str, limit: int = 20) -> ApiResult[list[TelegramUser]]:
  """Search contacts by query."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    result = await mtproto.invoke(ContactsSearchRequest(q=query, limit=limit))

    users = [build_user(u) for u in result.users[:limit]]
    return ApiResult(data=users, from_cache=False)
  except Exception:
    log.exception("Error searching contacts")
    return ApiResult(data=[], from_cache=False)


async def add_contact(
  first_name: str,
  last_name: str,
  phone_number: str,
  user_id: str | None = None,
) -> ApiResult[TelegramUser | None]:
  """Add a contact."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()
    client = mtproto.get_client()

    if user_id:
      entity = await client.get_entity(user_id)
      input_user = InputUser(
        user_id=entity.id,
        access_hash=getattr(entity, "access_hash", 0) or 0,
      )
    else:
      input_user = InputUser(user_id=0, access_hash=0)

    result = await mtproto.invoke(
      AddContactRequest(
        id=input_user,
        first_name=first_name,
        last_name=last_name,
        phone=phone_number,
        add_phone_privacy_exception=False,
      )
    )

    user = build_user(result.users[0]) if result.users else None
    return ApiResult(data=user, from_cache=False)
  except Exception:
    log.exception("Error adding contact")
    return ApiResult(data=None, from_cache=False)


async def delete_contact(user_id: str) -> ApiResult[bool]:
  """Delete a contact."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_entity(user_id)
    input_user = InputUser(
      user_id=entity.id,
      access_hash=getattr(entity, "access_hash", 0) or 0,
    )

    await mtproto.invoke(DeleteContactsRequest(id=[input_user]))
    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error deleting contact")
    return ApiResult(data=False, from_cache=False)


async def block_user(user_id: str) -> ApiResult[bool]:
  """Block a user."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_entity(user_id)
    input_peer = InputPeerUser(
      user_id=entity.id,
      access_hash=getattr(entity, "access_hash", 0) or 0,
    )

    await mtproto.invoke(BlockRequest(id=input_peer))
    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error blocking user")
    return ApiResult(data=False, from_cache=False)


async def unblock_user(user_id: str) -> ApiResult[bool]:
  """Unblock a user."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_entity(user_id)
    input_peer = InputPeerUser(
      user_id=entity.id,
      access_hash=getattr(entity, "access_hash", 0) or 0,
    )

    await mtproto.invoke(UnblockRequest(id=input_peer))
    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error unblocking user")
    return ApiResult(data=False, from_cache=False)


async def get_blocked_users(limit: int = 100) -> ApiResult[list[TelegramUser]]:
  """Get blocked users."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    result = await mtproto.invoke(GetBlockedRequest(offset=0, limit=limit))

    users = [build_user(u) for u in result.users]
    return ApiResult(data=users, from_cache=False)
  except Exception:
    log.exception("Error getting blocked users")
    return ApiResult(data=[], from_cache=False)


async def get_contact_ids() -> ApiResult[list[str]]:
  """Get contact IDs."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    result = await mtproto.invoke(GetContactIDsRequest(hash=0))

    ids = [str(cid) for cid in result]
    return ApiResult(data=ids, from_cache=False)
  except Exception:
    log.exception("Error getting contact IDs")
    return ApiResult(data=[], from_cache=False)


async def import_contacts(
  contact_list: list[dict[str, str]],
) -> ApiResult[list[TelegramUser]]:
  """Import contacts from a list."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()

    input_contacts = [
      InputPhoneContact(
        client_id=random.randint(0, 9_999_999_999),
        phone=c["phone"],
        first_name=c["firstName"],
        last_name=c.get("lastName", ""),
      )
      for c in contact_list
    ]

    result = await mtproto.invoke(ImportContactsRequest(contacts=input_contacts))

    users = [build_user(u) for u in result.users]
    return ApiResult(data=users, from_cache=False)
  except Exception:
    log.exception("Error importing contacts")
    return ApiResult(data=[], from_cache=False)


async def export_contacts() -> ApiResult[list[dict[str, str]]]:
  """Export all contacts."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    result = await mtproto.invoke(GetContactsRequest(hash=0))

    if not isinstance(result, contacts.Contacts):
      return ApiResult(data=[], from_cache=False)

    exported = []
    for user in result.users:
      u = build_user(user)
      exported.append(
        {
          "phone": u.phone_number or "",
          "firstName": u.first_name or "",
          "lastName": u.last_name or "",
        }
      )

    return ApiResult(data=exported, from_cache=False)
  except Exception:
    log.exception("Error exporting contacts")
    return ApiResult(data=[], from_cache=False)


async def get_direct_chat_by_contact(user_id: str) -> ApiResult[Any | None]:
  """Get direct chat for a contact (from cache)."""
  try:
    state = store.get_state()
    for chat in state.chats.values():
      if chat.type == "private" and chat.id == user_id:
        return ApiResult(data=chat, from_cache=True)
    return ApiResult(data=None, from_cache=True)
  except Exception:
    log.exception("Error getting direct chat by contact")
    return ApiResult(data=None, from_cache=True)


async def get_contact_chats(limit: int = 20) -> ApiResult[list[Any]]:
  """Get private chats (contacts) from cache."""
  try:
    state = store.get_state()
    contact_chats = [c for c in state.chats.values() if c.type == "private"][:limit]
    return ApiResult(data=contact_chats, from_cache=True)
  except Exception:
    log.exception("Error getting contact chats")
    return ApiResult(data=[], from_cache=True)


async def get_last_interaction(user_id: str) -> ApiResult[TelegramUser | None]:
  """Get last interaction with a user (from cache)."""
  try:
    state = store.get_state()
    all_messages: list[TelegramMessage] = []
    for chat_msgs in state.messages.values():
      for msg in chat_msgs.values():
        if msg.from_id == user_id:
          all_messages.append(msg)

    if all_messages:
      all_messages.sort(key=lambda m: m.date, reverse=True)
      # Get the user from the last message
      all_messages[0]
      # Find the user in users map
      user = state.users.get(user_id)
      if user:
        return ApiResult(data=user, from_cache=True)

    return ApiResult(data=None, from_cache=True)
  except Exception:
    log.exception("Error getting last interaction")
    return ApiResult(data=None, from_cache=True)
