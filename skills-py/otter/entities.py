"""
Entity emission — converts Otter.ai state into platform entities and relationships.

Two main functions:
  - emit_initial_entities: Emits meetings and speakers on load.
  - emit_summaries: Emits summary entities on tick.

Both accept upsert_entity_fn and upsert_relationship_fn callables that forward
to the host runtime via reverse RPC.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from .db.connection import get_db
from .state import store

if TYPE_CHECKING:
  from .state.types import OtterSpeech

log = logging.getLogger("skill.otter.entities")

SOURCE = "otter"

UpsertEntityFn = Callable[..., Awaitable[None]]
UpsertRelationshipFn = Callable[..., Awaitable[None]]


def _meeting_metadata(speech: OtterSpeech) -> dict[str, Any]:
  """Build metadata dict for a meeting entity."""
  meta: dict[str, Any] = {
    "title": speech.title,
    "duration": speech.duration,
    "created_at": speech.created_at,
    "speaker_count": speech.speaker_count,
    "word_count": speech.word_count,
    "is_processed": speech.is_processed,
  }
  if speech.summary:
    meta["summary"] = speech.summary
  return meta


async def emit_initial_entities(
  upsert_entity_fn: UpsertEntityFn,
  upsert_relationship_fn: UpsertRelationshipFn,
) -> None:
  """Emit all known meetings and speakers as platform entities.

  Called after successful auth during on_load, and again on each tick
  to refresh entity metadata.
  """
  state = store.get_state()

  # --- Emit meeting entities ---
  for speech_id in state.speeches_order:
    speech = state.speeches.get(speech_id)
    if not speech:
      continue

    try:
      await upsert_entity_fn(
        type="otter.meeting",
        source=SOURCE,
        source_id=speech.speech_id,
        title=speech.title or f"Meeting {speech.speech_id}",
        metadata=_meeting_metadata(speech),
      )
    except Exception:
      log.debug("Failed to upsert meeting entity %s", speech.speech_id, exc_info=True)

  # --- Emit speaker entities ---
  for _speaker_id, speaker in state.speakers.items():
    try:
      await upsert_entity_fn(
        type="otter.speaker",
        source=SOURCE,
        source_id=speaker.speaker_id,
        title=speaker.name or f"Speaker {speaker.speaker_id}",
        metadata={"name": speaker.name},
      )
    except Exception:
      log.debug("Failed to upsert speaker entity %s", speaker.speaker_id, exc_info=True)

    # Emit speaker_in relationships for all meetings
    # (we don't have per-meeting speaker data from the list API,
    #  so we emit relationships based on known speakers)
    for speech_id in state.speeches_order:
      try:
        await upsert_relationship_fn(
          source_id=f"{SOURCE}:{speaker.speaker_id}",
          target_id=f"{SOURCE}:{speech_id}",
          type="speaker_in",
          source=SOURCE,
        )
      except Exception:
        log.debug(
          "Failed to upsert speaker_in for %s -> %s",
          speaker.speaker_id,
          speech_id,
          exc_info=True,
        )

  log.info(
    "Emitted entities: %d meetings, %d speakers",
    len(state.speeches_order),
    len(state.speakers),
  )


async def emit_summaries(
  upsert_entity_fn: UpsertEntityFn,
  upsert_relationship_fn: UpsertRelationshipFn,
) -> None:
  """Emit the latest summaries as platform entities with relationships."""
  try:
    db = await get_db()
  except Exception:
    log.debug("Cannot get DB for summary emission", exc_info=True)
    return

  store.get_state()

  try:
    cursor = await db.execute(
      """SELECT summary_type, content, period_start, period_end
               FROM summaries
               ORDER BY created_at DESC
               LIMIT 4"""
    )
    rows = await cursor.fetchall()
  except Exception:
    log.debug("Failed to query summaries", exc_info=True)
    return

  import json

  for row in rows:
    summary_type = row[0]
    try:
      content = json.loads(row[1]) if isinstance(row[1], str) else row[1]
    except (json.JSONDecodeError, TypeError):
      content = {}
    period_start = row[2]
    period_end = row[3]

    entity_source_id = f"{summary_type}:{period_start}:{period_end}"

    try:
      start_str = time.strftime("%b %d %H:%M", time.localtime(period_start))
      end_str = time.strftime("%H:%M", time.localtime(period_end))
    except (OSError, ValueError):
      start_str = str(period_start)
      end_str = str(period_end)

    title = f"{summary_type.replace('_', ' ').title()} Summary ({start_str} - {end_str})"

    meta: dict[str, Any] = {
      "summary_type": summary_type,
      "start_date": period_start,
      "end_date": period_end,
    }

    try:
      await upsert_entity_fn(
        type="otter.summary",
        source=SOURCE,
        source_id=entity_source_id,
        title=title,
        metadata=meta,
      )
    except Exception:
      log.debug("Failed to upsert summary entity %s", entity_source_id, exc_info=True)
      continue

    # Emit summarizes relationships
    meeting_ids = content.get("meeting_ids", [])
    for meeting_id in meeting_ids:
      try:
        await upsert_relationship_fn(
          source_id=f"{SOURCE}:{entity_source_id}",
          target_id=f"{SOURCE}:{meeting_id}",
          type="summarizes",
          source=SOURCE,
        )
      except Exception:
        log.debug(
          "Failed to upsert summarizes for %s -> %s",
          entity_source_id,
          meeting_id,
          exc_info=True,
        )

  log.info("Emitted %d summary entities", len(list(rows)))
