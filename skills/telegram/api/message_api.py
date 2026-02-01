"""
Message API — Telethon wrappers for message operations.

Ported from api/message-api.ts. Cache-first pattern with rate limiting.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any, TypeVar, Generic

from telethon.tl.types import (
    Message,
    InputChannel,
    InputMessagesFilterPinned,
    InputMessagesFilterEmpty,
    ReactionEmoji,
    InputReplyToMessage,
    InputMediaPoll,
    Poll,
    PollAnswer,
    TextWithEntities,
    UpdateMessageID,
    Updates,
)
from telethon.tl.functions.messages import (
    GetHistoryRequest,
    EditMessageRequest,
    DeleteMessagesRequest,
    ForwardMessagesRequest,
    UpdatePinnedMessageRequest,
    ReadHistoryRequest,
    SearchRequest,
    SendReactionRequest,
    GetMessagesReactionsRequest,
    SaveDraftRequest,
    GetAllDraftsRequest,
    SendMediaRequest,
)
from telethon.tl.functions.channels import (
    ReadHistoryRequest as ChannelReadHistoryRequest,
)

try:
    from telethon.tl.functions.channels import GetForumTopicsRequest
except ImportError:
    GetForumTopicsRequest = None  # Not available in telethon < 1.43

from ..client.telethon_client import get_client
from ..client.builders import build_message
from ..state import store
from ..state.types import TelegramMessage
from ..helpers import enforce_rate_limit

log = logging.getLogger("skill.telegram.api.message")

T = TypeVar("T")


@dataclass
class ApiResult(Generic[T]):
    data: T
    from_cache: bool


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


async def send_message(
    chat_id: str | int,
    message: str,
    reply_to_message_id: int | None = None,
) -> dict[str, int]:
    """Send a message to a chat."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        chat = store.get_chat_by_id(str(chat_id))
        entity = chat.username if (chat and chat.username) else chat_id

        result = await mtproto.with_flood_wait_handling(
            lambda: client.send_message(
                entity,
                message,
                reply_to=reply_to_message_id,
            )
        )

        log.debug("Sent message to chat %s, ID: %s", chat_id, result.id)
        return {"id": result.id}
    except Exception:
        log.exception("Error sending message to chat %s", chat_id)
        raise


async def reply_to_message(
    chat_id: str | int,
    message_id: int,
    text: str,
) -> dict[str, int]:
    """Reply to a specific message."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        chat = store.get_chat_by_id(str(chat_id))
        entity = chat.username if (chat and chat.username) else chat_id

        result = await mtproto.with_flood_wait_handling(
            lambda: client.send_message(
                entity,
                text,
                reply_to=message_id,
            )
        )

        log.debug("Replied to message %d in chat %s, new ID: %s", message_id, chat_id, result.id)
        return {"id": result.id}
    except Exception:
        log.exception("Error replying to message %d in chat %s", message_id, chat_id)
        raise


async def edit_message(
    chat_id: str | int,
    message_id: int,
    new_text: str,
) -> dict[str, bool]:
    """Edit an existing message."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        await mtproto.with_flood_wait_handling(
            lambda: client(
                EditMessageRequest(
                    peer=entity,
                    id=message_id,
                    message=new_text,
                )
            )
        )

        log.debug("Edited message %d in chat %s", message_id, chat_id)
        return {"success": True}
    except Exception:
        log.exception("Error editing message %d in chat %s", message_id, chat_id)
        return {"success": False}


async def delete_message(
    chat_id: str | int,
    message_id: int,
    revoke: bool = True,
) -> dict[str, bool]:
    """Delete a message."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()

        await mtproto.with_flood_wait_handling(
            lambda: client(
                DeleteMessagesRequest(
                    id=[message_id],
                    revoke=revoke,
                )
            )
        )

        store.remove_message(str(chat_id), message_id)
        log.debug("Deleted message %d from chat %s", message_id, chat_id)
        return {"success": True}
    except Exception:
        log.exception("Error deleting message %d from chat %s", message_id, chat_id)
        return {"success": False}


async def forward_message(
    from_chat_id: str,
    to_chat_id: str,
    message_id: int,
) -> dict[str, int]:
    """Forward a message from one chat to another."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        from_entity = await client.get_input_entity(from_chat_id)
        to_entity = await client.get_input_entity(to_chat_id)

        result = await mtproto.with_flood_wait_handling(
            lambda: client(
                ForwardMessagesRequest(
                    from_peer=from_entity,
                    to_peer=to_entity,
                    id=[message_id],
                    random_id=[random.randint(0, 10**16)],
                )
            )
        )

        new_id = 0
        if isinstance(result, Updates):
            for update in result.updates:
                if isinstance(update, UpdateMessageID):
                    new_id = update.id
                    break

        log.debug(
            "Forwarded message %d from %s to %s, new ID: %d",
            message_id,
            from_chat_id,
            to_chat_id,
            new_id,
        )
        return {"id": new_id}
    except Exception:
        log.exception(
            "Error forwarding message %d from %s to %s", message_id, from_chat_id, to_chat_id
        )
        raise


async def pin_message(
    chat_id: str,
    message_id: int,
    notify: bool = True,
) -> dict[str, bool]:
    """Pin a message in a chat."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        await mtproto.with_flood_wait_handling(
            lambda: client(
                UpdatePinnedMessageRequest(
                    peer=entity,
                    id=message_id,
                    silent=not notify,
                )
            )
        )

        log.debug("Pinned message %d in chat %s", message_id, chat_id)
        return {"success": True}
    except Exception:
        log.exception("Error pinning message %d in chat %s", message_id, chat_id)
        return {"success": False}


async def unpin_message(
    chat_id: str,
    message_id: int,
) -> dict[str, bool]:
    """Unpin a message in a chat."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        await mtproto.with_flood_wait_handling(
            lambda: client(
                UpdatePinnedMessageRequest(
                    peer=entity,
                    id=message_id,
                    unpin=True,
                )
            )
        )

        log.debug("Unpinned message %d in chat %s", message_id, chat_id)
        return {"success": True}
    except Exception:
        log.exception("Error unpinning message %d in chat %s", message_id, chat_id)
        return {"success": False}


async def mark_as_read(chat_id: str) -> dict[str, bool]:
    """Mark messages as read in a chat."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)
        chat = store.get_chat_by_id(chat_id)

        is_channel = chat and chat.type in ("channel", "supergroup")

        if is_channel and isinstance(entity, InputChannel):
            await mtproto.with_flood_wait_handling(
                lambda: client(
                    ChannelReadHistoryRequest(
                        channel=entity,
                        max_id=0,
                    )
                )
            )
        else:
            await mtproto.with_flood_wait_handling(
                lambda: client(
                    ReadHistoryRequest(
                        peer=entity,
                        max_id=0,
                    )
                )
            )

        log.debug("Marked messages as read in chat %s", chat_id)
        return {"success": True}
    except Exception:
        log.exception("Error marking messages as read in chat %s", chat_id)
        return {"success": False}


async def get_pinned_messages(chat_id: str) -> ApiResult[list[TelegramMessage]]:
    """Get pinned messages from a chat."""
    try:
        await enforce_rate_limit("api_read")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        result = await mtproto.with_flood_wait_handling(
            lambda: client(
                SearchRequest(
                    peer=entity,
                    q="",
                    filter=InputMessagesFilterPinned(),
                    min_date=0,
                    max_date=0,
                    offset_id=0,
                    add_offset=0,
                    limit=100,
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
                built = build_message(msg, chat_id)
                if built:
                    messages.append(built)

        log.debug("Fetched %d pinned messages from chat %s", len(messages), chat_id)
        return ApiResult(data=messages, from_cache=False)
    except Exception:
        log.exception("Error fetching pinned messages from chat %s", chat_id)
        return ApiResult(data=[], from_cache=False)


async def send_reaction(
    chat_id: str,
    message_id: int,
    reaction: str,
) -> dict[str, bool]:
    """Send a reaction to a message."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        await mtproto.with_flood_wait_handling(
            lambda: client(
                SendReactionRequest(
                    peer=entity,
                    msg_id=message_id,
                    reaction=[ReactionEmoji(emoticon=reaction)],
                )
            )
        )

        log.debug("Sent reaction '%s' to message %d in chat %s", reaction, message_id, chat_id)
        return {"success": True}
    except Exception:
        log.exception("Error sending reaction to message %d in chat %s", message_id, chat_id)
        return {"success": False}


async def remove_reaction(
    chat_id: str,
    message_id: int,
    reaction: str | None = None,
) -> dict[str, bool]:
    """Remove a reaction from a message."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        await mtproto.with_flood_wait_handling(
            lambda: client(
                SendReactionRequest(
                    peer=entity,
                    msg_id=message_id,
                    reaction=[],
                )
            )
        )

        log.debug("Removed reaction from message %d in chat %s", message_id, chat_id)
        return {"success": True}
    except Exception:
        log.exception("Error removing reaction from message %d in chat %s", message_id, chat_id)
        return {"success": False}


async def get_message_reactions(
    chat_id: str,
    message_id: int,
) -> ApiResult[list[Any]]:
    """Get reactions for a message."""
    try:
        await enforce_rate_limit("api_read")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        result = await mtproto.with_flood_wait_handling(
            lambda: client(
                GetMessagesReactionsRequest(
                    peer=entity,
                    id=[message_id],
                )
            )
        )

        updates = getattr(result, "updates", [])
        log.debug("Fetched reactions for message %d in chat %s", message_id, chat_id)
        return ApiResult(data=updates, from_cache=False)
    except Exception:
        log.exception("Error fetching reactions for message %d in chat %s", message_id, chat_id)
        return ApiResult(data=[], from_cache=False)


async def get_history(
    chat_id: str,
    limit: int = 20,
    offset_id: int | None = None,
) -> ApiResult[list[TelegramMessage]]:
    """Get message history with offset."""
    try:
        await enforce_rate_limit("api_read")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        result = await mtproto.with_flood_wait_handling(
            lambda: client(
                GetHistoryRequest(
                    peer=entity,
                    limit=limit,
                    offset_id=offset_id or 0,
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
                built = build_message(msg, chat_id)
                if built:
                    messages.append(built)

        store.add_messages(chat_id, messages)
        log.debug("Fetched %d history messages from chat %s", len(messages), chat_id)
        return ApiResult(data=messages, from_cache=False)
    except Exception:
        log.exception("Error fetching history for chat %s", chat_id)
        return ApiResult(data=[], from_cache=False)


async def save_draft(
    chat_id: str,
    text: str,
    reply_to_msg_id: int | None = None,
) -> dict[str, bool]:
    """Save a draft message."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        kwargs: dict[str, Any] = {"peer": entity, "message": text}
        if reply_to_msg_id:
            kwargs["reply_to"] = InputReplyToMessage(reply_to_msg_id=reply_to_msg_id)

        await mtproto.with_flood_wait_handling(lambda: client(SaveDraftRequest(**kwargs)))

        log.debug("Saved draft in chat %s", chat_id)
        return {"success": True}
    except Exception:
        log.exception("Error saving draft in chat %s", chat_id)
        return {"success": False}


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


async def clear_draft(chat_id: str) -> dict[str, bool]:
    """Clear draft in a chat."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        await mtproto.with_flood_wait_handling(
            lambda: client(
                SaveDraftRequest(
                    peer=entity,
                    message="",
                )
            )
        )

        log.debug("Cleared draft in chat %s", chat_id)
        return {"success": True}
    except Exception:
        log.exception("Error clearing draft in chat %s", chat_id)
        return {"success": False}


async def create_poll(
    chat_id: str,
    question: str,
    options: list[str],
    anonymous: bool | None = None,
    multiple_choice: bool | None = None,
) -> dict[str, int]:
    """Create a poll in a chat."""
    try:
        await enforce_rate_limit("api_write")

        mtproto = get_client()
        client = mtproto.get_client()
        entity = await client.get_input_entity(chat_id)

        poll = Poll(
            id=random.randint(0, 10**16),
            question=TextWithEntities(text=question, entities=[]),
            answers=[
                PollAnswer(
                    text=TextWithEntities(text=opt, entities=[]),
                    option=bytes([idx]),
                )
                for idx, opt in enumerate(options)
            ],
            public_voters=not anonymous if anonymous is not None else None,
            multiple_choice=multiple_choice or False,
        )

        media = InputMediaPoll(poll=poll)

        result = await mtproto.with_flood_wait_handling(
            lambda: client(
                SendMediaRequest(
                    peer=entity,
                    media=media,
                    message="",
                    random_id=random.randint(0, 10**16),
                )
            )
        )

        new_id = 0
        if isinstance(result, Updates):
            for update in result.updates:
                if isinstance(update, UpdateMessageID):
                    new_id = update.id
                    break

        log.debug("Created poll in chat %s, message ID: %d", chat_id, new_id)
        return {"id": new_id}
    except Exception:
        log.exception("Error creating poll in chat %s", chat_id)
        raise


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
