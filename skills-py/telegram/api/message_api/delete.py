"""
Message delete functions — delete messages.
"""

from __future__ import annotations

import logging

from telethon.tl.functions.messages import DeleteMessagesRequest

from ...client.telethon_client import get_client
from ...helpers import enforce_rate_limit
from ...state import store

log = logging.getLogger("skill.telegram.api.message_api.delete")


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
