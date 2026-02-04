"""
Message reaction functions — send and remove reactions.
"""

from __future__ import annotations

import logging

from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji

from ...client.telethon_client import get_client
from ...helpers import enforce_rate_limit

log = logging.getLogger("skill.telegram.api.message_api.reaction")


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
