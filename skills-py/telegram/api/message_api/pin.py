"""
Message pin functions — pin and unpin messages.
"""

from __future__ import annotations

import logging

from telethon.tl.functions.messages import UpdatePinnedMessageRequest

from ...client.telethon_client import get_client
from ...helpers import enforce_rate_limit

log = logging.getLogger("skill.telegram.api.message_api.pin")


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
