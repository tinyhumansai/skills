"""
Settings API — Telethon wrappers for settings, profile, media operations.

Ported from api/settings-api.ts. Rate limited.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from telethon.tl.functions.account import (
  GetPrivacyRequest,
  SetPrivacyRequest,
  UpdateNotifySettingsRequest,
  UpdateProfileRequest,
)
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.functions.folders import EditPeerFoldersRequest
from telethon.tl.functions.photos import (
  DeletePhotosRequest,
  GetUserPhotosRequest,
  UpdateProfilePhotoRequest,
)
from telethon.tl.types import (
  BotCommand,
  BotCommandScopeDefault,
  BotCommandScopePeer,
  InputFolderPeer,
  InputNotifyPeer,
  InputPeerNotifySettings,
  InputPhoto,
  InputPhotoEmpty,
  InputPrivacyKeyChatInvite,
  InputPrivacyKeyForwards,
  InputPrivacyKeyPhoneCall,
  InputPrivacyKeyPhoneNumber,
  InputPrivacyKeyPhoneP2P,
  InputPrivacyKeyProfilePhoto,
  InputPrivacyKeyStatusTimestamp,
  InputPrivacyValueAllowAll,
  InputPrivacyValueAllowContacts,
  InputPrivacyValueDisallowAll,
  InputUser,
  photos,
)

from ..client.builders import build_user
from ..client.telethon_client import get_client
from ..helpers import enforce_rate_limit
from ..state import store

log = logging.getLogger("skill.telegram.api.settings")

T = TypeVar("T")


@dataclass
class ApiResult(Generic[T]):
  data: T
  from_cache: bool


async def mute_chat(chat_id: str, mute_for: int | None = None) -> ApiResult[bool]:
  """Mute a chat."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_input_entity(chat_id)

    mute_until = (math.floor(___import_time() / 1000) + mute_for) if mute_for else 2147483647

    await mtproto.invoke(
      UpdateNotifySettingsRequest(
        peer=InputNotifyPeer(peer=entity),
        settings=InputPeerNotifySettings(mute_until=mute_until),
      )
    )

    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error muting chat")
    return ApiResult(data=False, from_cache=False)


def ___import_time() -> float:
  import time

  return time.time() * 1000


async def unmute_chat(chat_id: str) -> ApiResult[bool]:
  """Unmute a chat."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_input_entity(chat_id)

    await mtproto.invoke(
      UpdateNotifySettingsRequest(
        peer=InputNotifyPeer(peer=entity),
        settings=InputPeerNotifySettings(mute_until=0),
      )
    )

    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error unmuting chat")
    return ApiResult(data=False, from_cache=False)


async def archive_chat(chat_id: str) -> ApiResult[bool]:
  """Archive a chat."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_input_entity(chat_id)

    await mtproto.invoke(
      EditPeerFoldersRequest(
        folder_peers=[InputFolderPeer(peer=entity, folder_id=1)],
      )
    )

    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error archiving chat")
    return ApiResult(data=False, from_cache=False)


async def unarchive_chat(chat_id: str) -> ApiResult[bool]:
  """Unarchive a chat."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_input_entity(chat_id)

    await mtproto.invoke(
      EditPeerFoldersRequest(
        folder_peers=[InputFolderPeer(peer=entity, folder_id=0)],
      )
    )

    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error unarchiving chat")
    return ApiResult(data=False, from_cache=False)


async def get_privacy_settings() -> ApiResult[Any]:
  """Get all privacy settings."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()

    keys = [
      ("statusTimestamp", InputPrivacyKeyStatusTimestamp()),
      ("chatInvite", InputPrivacyKeyChatInvite()),
      ("phoneCall", InputPrivacyKeyPhoneCall()),
      ("phoneP2P", InputPrivacyKeyPhoneP2P()),
      ("forwards", InputPrivacyKeyForwards()),
      ("profilePhoto", InputPrivacyKeyProfilePhoto()),
      ("phoneNumber", InputPrivacyKeyPhoneNumber()),
    ]

    result_data = {}
    for name, key in keys:
      try:
        r = await mtproto.invoke(GetPrivacyRequest(key=key))
        result_data[name] = [str(rule) for rule in r.rules]
      except Exception:
        result_data[name] = []

    return ApiResult(data=result_data, from_cache=False)
  except Exception:
    log.exception("Error getting privacy settings")
    return ApiResult(data={}, from_cache=False)


async def set_privacy_settings(setting: str, value: str) -> ApiResult[bool]:
  """Set a privacy setting."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()

    key_map = {
      "statusTimestamp": InputPrivacyKeyStatusTimestamp(),
      "chatInvite": InputPrivacyKeyChatInvite(),
      "phoneCall": InputPrivacyKeyPhoneCall(),
      "phoneP2P": InputPrivacyKeyPhoneP2P(),
      "forwards": InputPrivacyKeyForwards(),
      "profilePhoto": InputPrivacyKeyProfilePhoto(),
      "phoneNumber": InputPrivacyKeyPhoneNumber(),
    }

    key = key_map.get(setting)
    if not key:
      return ApiResult(data=False, from_cache=False)

    rule_map = {
      "everybody": [InputPrivacyValueAllowAll()],
      "contacts": [InputPrivacyValueAllowContacts()],
      "nobody": [InputPrivacyValueDisallowAll()],
    }

    rules = rule_map.get(value)
    if not rules:
      return ApiResult(data=False, from_cache=False)

    await mtproto.invoke(SetPrivacyRequest(key=key, rules=rules))
    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error setting privacy")
    return ApiResult(data=False, from_cache=False)


async def get_me() -> ApiResult[Any]:
  """Get the current user."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    me = await client.get_me()

    if not me:
      return ApiResult(data=None, from_cache=False)

    user = build_user(me)
    store.set_current_user(user)
    return ApiResult(data=user, from_cache=False)
  except Exception:
    log.exception("Error getting me")
    return ApiResult(data=None, from_cache=False)


async def update_profile(
  first_name: str | None = None,
  last_name: str | None = None,
  bio: str | None = None,
) -> ApiResult[Any]:
  """Update user profile."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()

    kwargs: dict[str, Any] = {}
    if first_name is not None:
      kwargs["first_name"] = first_name
    if last_name is not None:
      kwargs["last_name"] = last_name
    if bio is not None:
      kwargs["about"] = bio

    await mtproto.invoke(UpdateProfileRequest(**kwargs))
    return await get_me()
  except Exception:
    log.exception("Error updating profile")
    return ApiResult(data=None, from_cache=False)


async def get_user_photos(user_id: str, limit: int = 20) -> ApiResult[list[Any]]:
  """Get user profile photos."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_entity(user_id)
    input_user = InputUser(
      user_id=entity.id,
      access_hash=getattr(entity, "access_hash", 0) or 0,
    )

    result = await mtproto.invoke(
      GetUserPhotosRequest(
        user_id=input_user,
        offset=0,
        max_id=0,
        limit=limit,
      )
    )

    photo_list = []
    if isinstance(result, (photos.Photos, photos.PhotosSlice)):
      photo_list = result.photos

    return ApiResult(data=photo_list, from_cache=False)
  except Exception:
    log.exception("Error getting user photos")
    return ApiResult(data=[], from_cache=False)


async def get_user_status(user_id: str) -> ApiResult[Any]:
  """Get user online status."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_entity(user_id)

    status = getattr(entity, "status", None)
    return ApiResult(data=str(status) if status else None, from_cache=False)
  except Exception:
    log.exception("Error getting user status")
    return ApiResult(data=None, from_cache=False)


async def set_profile_photo(
  file_path: str | None = None,
  url: str | None = None,
) -> ApiResult[bool]:
  """Set profile photo (stub — file upload not yet implemented)."""
  await enforce_rate_limit("api_write")
  log.debug("setProfilePhoto is a stub — file upload not yet implemented")
  return ApiResult(data=False, from_cache=False)


async def delete_profile_photo(photo_id: str | None = None) -> ApiResult[bool]:
  """Delete a profile photo."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()

    if photo_id:
      input_photo = InputPhoto(
        id=int(photo_id),
        access_hash=0,
        file_reference=b"",
      )
      await mtproto.invoke(DeletePhotosRequest(id=[input_photo]))
    else:
      await mtproto.invoke(UpdateProfilePhotoRequest(id=InputPhotoEmpty()))

    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error deleting profile photo")
    return ApiResult(data=False, from_cache=False)


async def edit_chat_photo(
  chat_id: str,
  file_path: str | None = None,
) -> ApiResult[bool]:
  """Edit chat photo (stub — file upload not yet implemented)."""
  await enforce_rate_limit("api_write")
  log.debug("editChatPhoto is a stub — file upload not yet implemented")
  return ApiResult(data=False, from_cache=False)


async def get_bot_info(chat_id: str) -> ApiResult[Any]:
  """Get bot info for an entity."""
  await enforce_rate_limit("api_read")

  try:
    mtproto = get_client()
    client = mtproto.get_client()
    entity = await client.get_entity(chat_id)

    if getattr(entity, "bot", False):
      return ApiResult(
        data={
          "id": str(entity.id),
          "username": getattr(entity, "username", None),
          "firstName": getattr(entity, "first_name", None),
          "botInfoVersion": getattr(entity, "bot_info_version", None),
        },
        from_cache=False,
      )

    return ApiResult(data=None, from_cache=False)
  except Exception:
    log.exception("Error getting bot info")
    return ApiResult(data=None, from_cache=False)


async def set_bot_commands(
  commands: list[dict[str, str]],
  chat_id: str | None = None,
) -> ApiResult[bool]:
  """Set bot commands."""
  await enforce_rate_limit("api_write")

  try:
    mtproto = get_client()
    client = mtproto.get_client()

    if chat_id:
      entity = await client.get_input_entity(chat_id)
      scope = BotCommandScopePeer(peer=entity)
    else:
      scope = BotCommandScopeDefault()

    bot_commands = [
      BotCommand(command=cmd["command"], description=cmd["description"]) for cmd in commands
    ]

    await mtproto.invoke(
      SetBotCommandsRequest(
        scope=scope,
        lang_code="",
        commands=bot_commands,
      )
    )

    return ApiResult(data=True, from_cache=False)
  except Exception:
    log.exception("Error setting bot commands")
    return ApiResult(data=False, from_cache=False)
