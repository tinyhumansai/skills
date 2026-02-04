"""
Admin API — Telethon wrappers for admin/moderation operations.

Ported from api/admin-api.ts. Rate limited.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from telethon.tl.functions.channels import (
  EditAdminRequest,
  EditBannedRequest,
  GetAdminLogRequest,
  GetParticipantsRequest,
)
from telethon.tl.types import (
  Channel,
  ChannelParticipantsAdmins,
  ChannelParticipantsBanned,
  ChannelParticipantsBots,
  ChannelParticipantsKicked,
  ChannelParticipantsRecent,
  ChatAdminRights,
  ChatBannedRights,
  InputChannel,
  InputUser,
  channels,
)

from ..client.builders import build_user
from ..client.telethon_client import get_client
from ..helpers import enforce_rate_limit

log = logging.getLogger("skill.telegram.api.admin")

T = TypeVar("T")


@dataclass
class ApiResult(Generic[T]):
  data: T
  from_cache: bool


async def _get_input_channel(chat_id: str) -> InputChannel:
  """Get InputChannel for a chat ID."""
  mtproto = get_client()
  client = mtproto.get_client()
  entity = await client.get_entity(int(chat_id))
  if isinstance(entity, Channel):
    return InputChannel(
      channel_id=entity.id,
      access_hash=entity.access_hash or 0,
    )
  raise ValueError(f"Entity {chat_id} is not a channel")


async def _get_input_user(user_id: str) -> InputUser:
  """Get InputUser for a user ID."""
  mtproto = get_client()
  client = mtproto.get_client()
  entity = await client.get_entity(user_id)
  return InputUser(
    user_id=entity.id,
    access_hash=getattr(entity, "access_hash", 0) or 0,
  )


async def get_participants(
  chat_id: str,
  limit: int = 100,
  filter_type: str = "recent",
) -> ApiResult[list[Any]]:
  """Get channel/supergroup participants."""
  await enforce_rate_limit("api_read")

  try:
    channel = await _get_input_channel(chat_id)

    filter_map = {
      "admins": ChannelParticipantsAdmins(),
      "bots": ChannelParticipantsBots(),
      "kicked": ChannelParticipantsKicked(q=""),
      "banned": ChannelParticipantsBanned(q=""),
    }
    filter_obj = filter_map.get(filter_type, ChannelParticipantsRecent())

    mtproto = get_client()
    result = await mtproto.invoke(
      GetParticipantsRequest(
        channel=channel,
        filter=filter_obj,
        offset=0,
        limit=limit,
        hash=0,
      )
    )

    if not isinstance(result, channels.ChannelParticipants):
      return ApiResult(data=[], from_cache=False)

    participants = []
    for idx, p in enumerate(result.participants):
      user = build_user(result.users[idx]) if idx < len(result.users) else None
      participants.append({"participant": str(p), "user": user})

    return ApiResult(data=participants, from_cache=False)
  except Exception:
    log.exception("Error getting participants")
    return ApiResult(data=[], from_cache=False)


async def get_admins(chat_id: str) -> ApiResult[list[Any]]:
  """Get admins of a channel/supergroup."""
  await enforce_rate_limit("api_read")

  try:
    channel = await _get_input_channel(chat_id)
    mtproto = get_client()

    result = await mtproto.invoke(
      GetParticipantsRequest(
        channel=channel,
        filter=ChannelParticipantsAdmins(),
        offset=0,
        limit=100,
        hash=0,
      )
    )

    if not isinstance(result, channels.ChannelParticipants):
      return ApiResult(data=[], from_cache=False)

    admins = []
    for idx, p in enumerate(result.participants):
      user = build_user(result.users[idx]) if idx < len(result.users) else None
      admins.append({"participant": str(p), "user": user})

    return ApiResult(data=admins, from_cache=False)
  except Exception:
    log.exception("Error getting admins")
    return ApiResult(data=[], from_cache=False)


async def get_banned_users(chat_id: str, limit: int = 100) -> ApiResult[list[Any]]:
  """Get banned/kicked users."""
  await enforce_rate_limit("api_read")

  try:
    channel = await _get_input_channel(chat_id)
    mtproto = get_client()

    result = await mtproto.invoke(
      GetParticipantsRequest(
        channel=channel,
        filter=ChannelParticipantsKicked(q=""),
        offset=0,
        limit=limit,
        hash=0,
      )
    )

    if not isinstance(result, channels.ChannelParticipants):
      return ApiResult(data=[], from_cache=False)

    banned = []
    for idx, p in enumerate(result.participants):
      user = build_user(result.users[idx]) if idx < len(result.users) else None
      banned.append({"participant": str(p), "user": user})

    return ApiResult(data=banned, from_cache=False)
  except Exception:
    log.exception("Error getting banned users")
    return ApiResult(data=[], from_cache=False)


async def promote_admin(
  chat_id: str,
  user_id: str,
  title: str | None = None,
) -> ApiResult[bool]:
  """Promote a user to admin."""
  await enforce_rate_limit("api_write")

  try:
    channel = await _get_input_channel(chat_id)
    user = await _get_input_user(user_id)

    admin_rights = ChatAdminRights(
      change_info=True,
      post_messages=True,
      edit_messages=True,
      delete_messages=True,
      ban_users=True,
      invite_users=True,
      pin_messages=True,
      add_admins=False,
      anonymous=False,
      manage_call=True,
      other=True,
      manage_topics=True,
      post_stories=True,
      edit_stories=True,
      delete_stories=True,
    )

    mtproto = get_client()
    await mtproto.invoke(
      EditAdminRequest(
        channel=channel,
        user_id=user,
        admin_rights=admin_rights,
        rank=title or "",
      )
    )

    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error promoting admin")
    return ApiResult(data=False, from_cache=False)


async def demote_admin(chat_id: str, user_id: str) -> ApiResult[bool]:
  """Demote an admin to regular user."""
  await enforce_rate_limit("api_write")

  try:
    channel = await _get_input_channel(chat_id)
    user = await _get_input_user(user_id)

    no_rights = ChatAdminRights(
      change_info=False,
      post_messages=False,
      edit_messages=False,
      delete_messages=False,
      ban_users=False,
      invite_users=False,
      pin_messages=False,
      add_admins=False,
      anonymous=False,
      manage_call=False,
      other=False,
      manage_topics=False,
      post_stories=False,
      edit_stories=False,
      delete_stories=False,
    )

    mtproto = get_client()
    await mtproto.invoke(
      EditAdminRequest(
        channel=channel,
        user_id=user,
        admin_rights=no_rights,
        rank="",
      )
    )

    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error demoting admin")
    return ApiResult(data=False, from_cache=False)


async def ban_user(
  chat_id: str,
  user_id: str,
  until_date: int | None = None,
) -> ApiResult[bool]:
  """Ban a user from a channel/supergroup."""
  await enforce_rate_limit("api_write")

  try:
    channel = await _get_input_channel(chat_id)
    user = await _get_input_user(user_id)

    banned_rights = ChatBannedRights(
      view_messages=True,
      send_messages=True,
      send_media=True,
      send_stickers=True,
      send_gifs=True,
      send_games=True,
      send_inline=True,
      embed_links=True,
      send_polls=True,
      change_info=True,
      invite_users=True,
      pin_messages=True,
      manage_topics=True,
      send_photos=True,
      send_videos=True,
      send_roundvideos=True,
      send_audios=True,
      send_voices=True,
      send_docs=True,
      send_plain=True,
      until_date=until_date or 0,
    )

    mtproto = get_client()
    await mtproto.invoke(
      EditBannedRequest(
        channel=channel,
        participant=user,
        banned_rights=banned_rights,
      )
    )

    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error banning user")
    return ApiResult(data=False, from_cache=False)


async def unban_user(chat_id: str, user_id: str) -> ApiResult[bool]:
  """Unban a user from a channel/supergroup."""
  await enforce_rate_limit("api_write")

  try:
    channel = await _get_input_channel(chat_id)
    user = await _get_input_user(user_id)

    no_restrictions = ChatBannedRights(
      view_messages=False,
      send_messages=False,
      send_media=False,
      send_stickers=False,
      send_gifs=False,
      send_games=False,
      send_inline=False,
      embed_links=False,
      send_polls=False,
      change_info=False,
      invite_users=False,
      pin_messages=False,
      manage_topics=False,
      send_photos=False,
      send_videos=False,
      send_roundvideos=False,
      send_audios=False,
      send_voices=False,
      send_docs=False,
      send_plain=False,
      until_date=0,
    )

    mtproto = get_client()
    await mtproto.invoke(
      EditBannedRequest(
        channel=channel,
        participant=user,
        banned_rights=no_restrictions,
      )
    )

    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error unbanning user")
    return ApiResult(data=False, from_cache=False)


async def get_recent_actions(chat_id: str, limit: int = 20) -> ApiResult[list[Any]]:
  """Get recent admin actions (admin log)."""
  await enforce_rate_limit("api_read")

  try:
    channel = await _get_input_channel(chat_id)
    mtproto = get_client()

    result = await mtproto.invoke(
      GetAdminLogRequest(
        channel=channel,
        q="",
        events_filter=None,
        admins=None,
        max_id=0,
        min_id=0,
        limit=limit,
      )
    )

    actions = [
      {
        "id": str(event.id),
        "date": event.date,
        "userId": str(event.user_id),
        "action": str(event.action),
      }
      for event in result.events
    ]

    return ApiResult(data=actions, from_cache=False)
  except Exception:
    log.exception("Error getting recent actions")
    return ApiResult(data=[], from_cache=False)
