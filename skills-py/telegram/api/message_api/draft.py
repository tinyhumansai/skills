"""
Message draft functions — save and clear drafts.
"""

from __future__ import annotations

import logging
from typing import Any

from telethon.tl.functions.messages import SaveDraftRequest
from telethon.tl.types import InputReplyToMessage

from ...client.telethon_client import get_client
from ...helpers import enforce_rate_limit

log = logging.getLogger("skill.telegram.api.message_api.draft")


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
