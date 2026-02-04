"""
Message forward functions — forward messages between chats.
"""

from __future__ import annotations

import logging
import random

from telethon.tl.functions.messages import ForwardMessagesRequest
from telethon.tl.types import UpdateMessageID, Updates

from ...client.telethon_client import get_client
from ...helpers import enforce_rate_limit

log = logging.getLogger("skill.telegram.api.message_api.forward")


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
    log.exception("Error forwarding message %d from %s to %s", message_id, from_chat_id, to_chat_id)
    raise
