"""
Message edit functions — edit existing messages.
"""

from __future__ import annotations

import logging

from telethon.tl.functions.messages import EditMessageRequest

from ...client.telethon_client import get_client
from ...helpers import enforce_rate_limit

log = logging.getLogger("skill.telegram.api.message_api.edit")


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
