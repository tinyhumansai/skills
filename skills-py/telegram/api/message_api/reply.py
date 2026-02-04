"""
Message reply functions — reply to messages.
"""

from __future__ import annotations

import logging

from ...client.telethon_client import get_client
from ...helpers import enforce_rate_limit
from ...state import store

log = logging.getLogger("skill.telegram.api.message_api.reply")


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
