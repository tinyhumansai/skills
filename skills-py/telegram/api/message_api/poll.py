"""
Message poll functions — create polls.
"""

from __future__ import annotations

import logging
import random

from telethon.tl.functions.messages import SendMediaRequest
from telethon.tl.types import (
  InputMediaPoll,
  Poll,
  PollAnswer,
  TextWithEntities,
  UpdateMessageID,
  Updates,
)

from ...client.telethon_client import get_client
from ...helpers import enforce_rate_limit

log = logging.getLogger("skill.telegram.api.message_api.poll")


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
