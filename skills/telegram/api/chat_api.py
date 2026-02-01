"""
Chat API — Telethon wrappers for chat operations.

Ported from api/chat-api.ts. Cache-first pattern with rate limiting.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, TypeVar, Generic

from telethon.tl.types import (
    Channel,
    Chat,
    User,
    InputPeerEmpty,
    InputChannel,
    InputUser,
    InputChatPhotoEmpty,
    ChatInviteExported,
)
from telethon.tl.functions.messages import (
    GetDialogsRequest,
    CreateChatRequest,
    EditChatTitleRequest,
    EditChatPhotoRequest,
    DeleteChatUserRequest,
    ExportChatInviteRequest,
    ImportChatInviteRequest,
    AddChatUserRequest,
)
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    InviteToChannelRequest,
    EditTitleRequest as ChannelEditTitleRequest,
    EditPhotoRequest as ChannelEditPhotoRequest,
    LeaveChannelRequest,
    JoinChannelRequest,
)

from ..client.telethon_client import get_client
from ..client.builders import build_chat, build_user
from ..state import store
from ..state.types import TelegramChat
from ..helpers import enforce_rate_limit

log = logging.getLogger("skill.telegram.api.chat")

T = TypeVar("T")


@dataclass
class ApiResult(Generic[T]):
    data: T
    from_cache: bool


async def get_chats(limit: int = 20) -> ApiResult[list[TelegramChat]]:
    """Get list of chats (cache-first)."""
    cached = store.get_ordered_chats(limit)
    if cached:
        log.debug("getChats: returning %d chats from cache", len(cached))
        return ApiResult(data=cached, from_cache=True)

    log.debug("getChats: fetching from API, limit=%d", limit)
    await enforce_rate_limit("api_read")

    try:
        mtproto = get_client()
        client = mtproto.get_client()

        dialogs = await mtproto.with_flood_wait_handling(lambda: client.get_dialogs(limit=limit))

        chats: list[TelegramChat] = []
        for d in dialogs:
            chat = build_chat(d.dialog, d.entity)
            if d.message:
                from ..client.builders import build_message

                last_msg = build_message(d.message, chat.id)
                if last_msg:
                    chat.last_message = last_msg
                    chat.last_message_date = last_msg.date
            chats.append(chat)

        store.add_chats(chats)
        log.debug("getChats: fetched %d chats from API", len(chats))
        return ApiResult(data=chats, from_cache=False)
    except Exception:
        log.exception("getChats: error fetching chats")
        return ApiResult(data=[], from_cache=False)


async def get_chat(chat_id: str | int) -> ApiResult[TelegramChat | None]:
    """Get a specific chat by ID (cache-first)."""
    chat_id_str = str(chat_id)

    cached = store.get_chat_by_id(chat_id_str)
    if cached:
        log.debug("getChat: returning chat %s from cache", chat_id_str)
        return ApiResult(data=cached, from_cache=True)

    log.debug("getChat: fetching chat %s from API", chat_id_str)
    await enforce_rate_limit("api_read")

    try:
        mtproto = get_client()
        client = mtproto.get_client()
        entity = await mtproto.with_flood_wait_handling(lambda: client.get_entity(chat_id))

        chat = build_chat(entity)
        store.add_chats([chat])
        log.debug("getChat: fetched chat %s from API", chat_id_str)
        return ApiResult(data=chat, from_cache=False)
    except Exception:
        log.exception("getChat: error fetching chat %s", chat_id_str)
        return ApiResult(data=None, from_cache=False)


async def create_group(title: str, user_ids: list[str]) -> ApiResult[TelegramChat | None]:
    """Create a new group chat."""
    log.debug("createGroup: title=%s, userIds=%s", title, user_ids)
    await enforce_rate_limit("api_write")

    try:
        mtproto = get_client()
        client = mtproto.get_client()

        input_users: list[Any] = []
        for uid in user_ids:
            entity = await client.get_entity(uid)
            if isinstance(entity, User):
                input_users.append(
                    InputUser(
                        user_id=entity.id,
                        access_hash=entity.access_hash or 0,
                    )
                )

        if not input_users:
            log.debug("createGroup: no valid users provided")
            return ApiResult(data=None, from_cache=False)

        result = await mtproto.with_flood_wait_handling(
            lambda: client(CreateChatRequest(users=input_users, title=title))
        )

        if hasattr(result, "chats") and result.chats:
            chat = build_chat(result.chats[0])
            store.add_chats([chat])
            log.debug("createGroup: created group %s", chat.id)
            return ApiResult(data=chat, from_cache=False)

        return ApiResult(data=None, from_cache=False)
    except Exception:
        log.exception("createGroup: error creating group")
        return ApiResult(data=None, from_cache=False)


async def create_channel(
    title: str,
    description: str | None = None,
    megagroup: bool = False,
) -> ApiResult[TelegramChat | None]:
    """Create a new channel or megagroup."""
    log.debug("createChannel: title=%s, megagroup=%s", title, megagroup)
    await enforce_rate_limit("api_write")

    try:
        mtproto = get_client()
        client = mtproto.get_client()

        result = await mtproto.with_flood_wait_handling(
            lambda: client(
                CreateChannelRequest(
                    title=title,
                    about=description or "",
                    megagroup=megagroup,
                )
            )
        )

        if hasattr(result, "chats") and result.chats:
            chat = build_chat(result.chats[0])
            store.add_chats([chat])
            log.debug("createChannel: created channel %s", chat.id)
            return ApiResult(data=chat, from_cache=False)

        return ApiResult(data=None, from_cache=False)
    except Exception:
        log.exception("createChannel: error creating channel")
        return ApiResult(data=None, from_cache=False)


async def invite_to_group(chat_id: str, user_ids: list[str]) -> ApiResult[bool]:
    """Invite users to a group or channel."""
    log.debug("inviteToGroup: chatId=%s, userIds=%s", chat_id, user_ids)
    await enforce_rate_limit("api_write")

    try:
        mtproto = get_client()
        client = mtproto.get_client()

        chat_result = await get_chat(chat_id)
        if not chat_result.data:
            return ApiResult(data=False, from_cache=False)

        input_users: list[Any] = []
        for uid in user_ids:
            entity = await client.get_entity(uid)
            if isinstance(entity, User):
                input_users.append(
                    InputUser(
                        user_id=entity.id,
                        access_hash=entity.access_hash or 0,
                    )
                )

        if not input_users:
            return ApiResult(data=False, from_cache=False)

        chat_data = chat_result.data
        if chat_data.type in ("channel", "supergroup"):
            channel_entity = await client.get_entity(int(chat_id))
            if isinstance(channel_entity, Channel):
                input_channel = InputChannel(
                    channel_id=channel_entity.id,
                    access_hash=channel_entity.access_hash or 0,
                )
                await mtproto.with_flood_wait_handling(
                    lambda: client(
                        InviteToChannelRequest(
                            channel=input_channel,
                            users=input_users,
                        )
                    )
                )
        else:
            for iu in input_users:
                await mtproto.with_flood_wait_handling(
                    lambda: client(
                        AddChatUserRequest(
                            chat_id=int(chat_id),
                            user_id=iu,
                            fwd_limit=100,
                        )
                    )
                )

        log.debug("inviteToGroup: successfully invited users")
        return ApiResult(data=True, from_cache=False)
    except Exception:
        log.exception("inviteToGroup: error inviting users")
        return ApiResult(data=False, from_cache=False)


async def edit_chat_title(chat_id: str, new_title: str) -> ApiResult[bool]:
    """Edit chat title."""
    log.debug("editChatTitle: chatId=%s, newTitle=%s", chat_id, new_title)
    await enforce_rate_limit("api_write")

    try:
        mtproto = get_client()
        client = mtproto.get_client()

        chat_result = await get_chat(chat_id)
        if not chat_result.data:
            return ApiResult(data=False, from_cache=False)

        chat_data = chat_result.data
        if chat_data.type in ("channel", "supergroup"):
            entity = await client.get_entity(int(chat_id))
            if isinstance(entity, Channel):
                await mtproto.with_flood_wait_handling(
                    lambda: client(
                        ChannelEditTitleRequest(
                            channel=InputChannel(
                                channel_id=entity.id,
                                access_hash=entity.access_hash or 0,
                            ),
                            title=new_title,
                        )
                    )
                )
        else:
            await mtproto.with_flood_wait_handling(
                lambda: client(
                    EditChatTitleRequest(
                        chat_id=int(chat_id),
                        title=new_title,
                    )
                )
            )

        store.update_chat(chat_id, {"title": new_title})
        log.debug("editChatTitle: successfully updated title")
        return ApiResult(data=True, from_cache=False)
    except Exception:
        log.exception("editChatTitle: error updating title")
        return ApiResult(data=False, from_cache=False)


async def delete_chat_photo(chat_id: str) -> ApiResult[bool]:
    """Delete chat photo."""
    log.debug("deleteChatPhoto: chatId=%s", chat_id)
    await enforce_rate_limit("api_write")

    try:
        mtproto = get_client()
        client = mtproto.get_client()

        chat_result = await get_chat(chat_id)
        if not chat_result.data:
            return ApiResult(data=False, from_cache=False)

        empty_photo = InputChatPhotoEmpty()
        chat_data = chat_result.data
        if chat_data.type in ("channel", "supergroup"):
            entity = await client.get_entity(int(chat_id))
            if isinstance(entity, Channel):
                await mtproto.with_flood_wait_handling(
                    lambda: client(
                        ChannelEditPhotoRequest(
                            channel=InputChannel(
                                channel_id=entity.id,
                                access_hash=entity.access_hash or 0,
                            ),
                            photo=empty_photo,
                        )
                    )
                )
        else:
            await mtproto.with_flood_wait_handling(
                lambda: client(
                    EditChatPhotoRequest(
                        chat_id=int(chat_id),
                        photo=empty_photo,
                    )
                )
            )

        log.debug("deleteChatPhoto: successfully deleted photo")
        return ApiResult(data=True, from_cache=False)
    except Exception:
        log.exception("deleteChatPhoto: error deleting photo")
        return ApiResult(data=False, from_cache=False)


async def leave_chat(chat_id: str) -> ApiResult[bool]:
    """Leave a chat or channel."""
    log.debug("leaveChat: chatId=%s", chat_id)
    await enforce_rate_limit("api_write")

    try:
        mtproto = get_client()
        client = mtproto.get_client()

        chat_result = await get_chat(chat_id)
        if not chat_result.data:
            return ApiResult(data=False, from_cache=False)

        chat_data = chat_result.data
        if chat_data.type in ("channel", "supergroup"):
            entity = await client.get_entity(int(chat_id))
            if isinstance(entity, Channel):
                await mtproto.with_flood_wait_handling(
                    lambda: client(
                        LeaveChannelRequest(
                            channel=InputChannel(
                                channel_id=entity.id,
                                access_hash=entity.access_hash or 0,
                            ),
                        )
                    )
                )
        else:
            me = await client.get_me()
            await mtproto.with_flood_wait_handling(
                lambda: client(
                    DeleteChatUserRequest(
                        chat_id=int(chat_id),
                        user_id=InputUser(
                            user_id=me.id,
                            access_hash=me.access_hash or 0,
                        ),
                    )
                )
            )

        store.remove_chat(chat_id)
        log.debug("leaveChat: successfully left chat")
        return ApiResult(data=True, from_cache=False)
    except Exception:
        log.exception("leaveChat: error leaving chat")
        return ApiResult(data=False, from_cache=False)


async def get_invite_link(chat_id: str) -> ApiResult[str | None]:
    """Get invite link for a chat."""
    log.debug("getInviteLink: chatId=%s", chat_id)
    await enforce_rate_limit("api_read")

    try:
        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        result = await mtproto.with_flood_wait_handling(
            lambda: client(ExportChatInviteRequest(peer=entity))
        )

        if isinstance(result, ChatInviteExported):
            return ApiResult(data=result.link, from_cache=False)

        return ApiResult(data=None, from_cache=False)
    except Exception:
        log.exception("getInviteLink: error getting invite link")
        return ApiResult(data=None, from_cache=False)


async def export_chat_invite(
    chat_id: str,
    expire_date: int | None = None,
    usage_limit: int | None = None,
) -> ApiResult[str | None]:
    """Export a chat invite with custom parameters."""
    log.debug("exportChatInvite: chatId=%s", chat_id)
    await enforce_rate_limit("api_write")

    try:
        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        result = await mtproto.with_flood_wait_handling(
            lambda: client(
                ExportChatInviteRequest(
                    peer=entity,
                    expire_date=expire_date,
                    usage_limit=usage_limit,
                )
            )
        )

        if isinstance(result, ChatInviteExported):
            return ApiResult(data=result.link, from_cache=False)

        return ApiResult(data=None, from_cache=False)
    except Exception:
        log.exception("exportChatInvite: error exporting invite")
        return ApiResult(data=None, from_cache=False)


async def import_chat_invite(invite_hash: str) -> ApiResult[TelegramChat | None]:
    """Import a chat invite by hash."""
    log.debug("importChatInvite: inviteHash=%s", invite_hash)
    await enforce_rate_limit("api_write")

    try:
        mtproto = get_client()
        client = mtproto.get_client()

        result = await mtproto.with_flood_wait_handling(
            lambda: client(ImportChatInviteRequest(hash=invite_hash))
        )

        if hasattr(result, "chats") and result.chats:
            chat = build_chat(result.chats[0])
            store.add_chats([chat])
            log.debug("importChatInvite: joined chat %s", chat.id)
            return ApiResult(data=chat, from_cache=False)

        return ApiResult(data=None, from_cache=False)
    except Exception:
        log.exception("importChatInvite: error importing invite")
        return ApiResult(data=None, from_cache=False)


async def join_chat_by_link(invite_link: str) -> ApiResult[TelegramChat | None]:
    """Join a chat by invite link."""
    log.debug("joinChatByLink: inviteLink=%s", invite_link)

    hash_match = re.search(r"(?:joinchat/|\+)([A-Za-z0-9_-]+)", invite_link)
    if not hash_match:
        log.debug("joinChatByLink: could not extract hash from link")
        return ApiResult(data=None, from_cache=False)

    invite_hash = hash_match.group(1)
    return await import_chat_invite(invite_hash)


async def subscribe_public_channel(username: str) -> ApiResult[TelegramChat | None]:
    """Subscribe to a public channel by username."""
    log.debug("subscribePublicChannel: username=%s", username)
    await enforce_rate_limit("api_write")

    try:
        mtproto = get_client()
        client = mtproto.get_client()

        clean_username = username.lstrip("@")
        entity = await mtproto.with_flood_wait_handling(lambda: client.get_entity(clean_username))

        if not isinstance(entity, Channel):
            log.debug("subscribePublicChannel: entity is not a channel")
            return ApiResult(data=None, from_cache=False)

        result = await mtproto.with_flood_wait_handling(
            lambda: client(
                JoinChannelRequest(
                    channel=InputChannel(
                        channel_id=entity.id,
                        access_hash=entity.access_hash or 0,
                    ),
                )
            )
        )

        if hasattr(result, "chats") and result.chats:
            chat = build_chat(result.chats[0])
            store.add_chats([chat])
            log.debug("subscribePublicChannel: joined channel %s", chat.id)
            return ApiResult(data=chat, from_cache=False)

        return ApiResult(data=None, from_cache=False)
    except Exception:
        log.exception("subscribePublicChannel: error subscribing")
        return ApiResult(data=None, from_cache=False)
