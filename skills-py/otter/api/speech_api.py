"""
Speech/transcript API wrappers — high-level functions that coordinate
between the HTTP client, state store, and database.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from ..db import queries
from ..db.connection import get_db
from ..helpers import enforce_rate_limit
from ..state import store
from ..state.types import OtterSpeaker, OtterSpeech, OtterTranscriptSegment, OtterUser

if TYPE_CHECKING:
  from ..client.otter_client import OtterClient

log = logging.getLogger("skill.otter.api.speech")

_client: OtterClient | None = None


def set_client(client: OtterClient) -> None:
  global _client
  _client = client


def get_client() -> OtterClient:
  if _client is None:
    raise RuntimeError("Otter client not initialized")
  return _client


# ---------------------------------------------------------------------------
# Speech list
# ---------------------------------------------------------------------------


def _parse_speech(raw: dict[str, Any]) -> OtterSpeech:
  """Parse a raw API speech object into an OtterSpeech model."""
  return OtterSpeech(
    speech_id=str(raw.get("id", raw.get("speech_id", ""))),
    title=raw.get("title", ""),
    created_at=raw.get("created_at", raw.get("start_time", 0)),
    duration=raw.get("duration", raw.get("end_time", 0) - raw.get("start_time", 0)),
    summary=raw.get("summary"),
    speaker_count=raw.get("speaker_count", 0),
    word_count=raw.get("word_count", 0),
    folder_id=raw.get("folder_id"),
    is_processed=raw.get("is_processed", raw.get("status") == "done"),
    raw_json=raw,
  )


def _parse_speaker(raw: dict[str, Any]) -> OtterSpeaker:
  """Parse a raw API speaker object into an OtterSpeaker model."""
  return OtterSpeaker(
    speaker_id=str(raw.get("id", raw.get("speaker_id", ""))),
    name=raw.get("name", raw.get("display_name", "")),
  )


def _parse_transcript_segment(raw: dict[str, Any]) -> OtterTranscriptSegment:
  """Parse a raw API transcript segment."""
  return OtterTranscriptSegment(
    text=raw.get("text", ""),
    start_offset=raw.get("start_offset", raw.get("start", 0)),
    end_offset=raw.get("end_offset", raw.get("end", 0)),
    speaker_id=raw.get("speaker_id"),
    speaker_name=raw.get("speaker_name", raw.get("speaker")),
  )


async def fetch_speeches(limit: int = 50, folder: str | None = None) -> list[OtterSpeech]:
  """Fetch speech list from API, update state and DB."""
  await enforce_rate_limit("api_read")
  client = get_client()

  result = await client.get_speeches(limit=limit, folder=folder)

  # Handle both list and dict responses
  raw_speeches = (
    result if isinstance(result, list) else result.get("speeches", result.get("data", []))
  )
  if not isinstance(raw_speeches, list):
    raw_speeches = []

  speeches = [_parse_speech(s) for s in raw_speeches]

  # Update state
  speeches_dict = {s.speech_id: s for s in speeches}
  order = [s.speech_id for s in speeches]
  store.set_speeches(speeches_dict, order)

  # Update DB
  try:
    db = await get_db()
    await queries.upsert_speeches_batch(db, speeches)
  except Exception:
    log.debug("Failed to cache speeches in DB", exc_info=True)

  store.set_sync_status(last_sync=time.time())
  return speeches


async def fetch_speech(speech_id: str) -> OtterSpeech | None:
  """Fetch a single speech with its transcript."""
  await enforce_rate_limit("api_read")
  client = get_client()

  raw = await client.get_speech(speech_id)
  if not raw:
    return None

  speech = _parse_speech(raw)
  store.add_speech(speech)

  try:
    db = await get_db()
    await queries.upsert_speech(db, speech)
    await db.commit()
  except Exception:
    log.debug("Failed to cache speech in DB", exc_info=True)

  return speech


async def fetch_transcript(speech_id: str) -> list[OtterTranscriptSegment]:
  """Fetch transcript segments for a speech."""
  await enforce_rate_limit("api_read")
  client = get_client()

  result = await client.get_transcript(speech_id)

  # Handle response format
  raw_segments = (
    result if isinstance(result, list) else result.get("transcript", result.get("segments", []))
  )
  if not isinstance(raw_segments, list):
    # May be plain text
    text = result.get("text", "")
    if text:
      return [OtterTranscriptSegment(text=text)]
    return []

  segments = [_parse_transcript_segment(s) for s in raw_segments]

  # Cache in DB
  try:
    db = await get_db()
    await queries.upsert_transcript_segments(db, speech_id, segments)
  except Exception:
    log.debug("Failed to cache transcript in DB", exc_info=True)

  return segments


async def fetch_user() -> OtterUser | None:
  """Fetch the current user profile."""
  await enforce_rate_limit("api_read")
  client = get_client()

  raw = await client.get_user()
  if not raw:
    return None

  user = OtterUser(
    id=str(raw.get("id", raw.get("user_id", ""))),
    email=raw.get("email", ""),
    name=raw.get("name", raw.get("display_name", "")),
  )
  store.set_current_user(user)
  return user


async def fetch_speakers() -> list[OtterSpeaker]:
  """Fetch recognized speakers."""
  await enforce_rate_limit("api_read")
  client = get_client()

  result = await client.get_speakers()

  raw_speakers = (
    result if isinstance(result, list) else result.get("speakers", result.get("data", []))
  )
  if not isinstance(raw_speakers, list):
    raw_speakers = []

  speakers = [_parse_speaker(s) for s in raw_speakers]

  # Update state
  speakers_dict = {s.speaker_id: s for s in speakers}
  store.set_speakers(speakers_dict)

  # Cache in DB
  try:
    db = await get_db()
    await queries.upsert_speakers_batch(db, speakers)
  except Exception:
    log.debug("Failed to cache speakers in DB", exc_info=True)

  return speakers


async def search_speeches(query: str, limit: int = 20) -> list[OtterSpeech]:
  """Search across all speeches via API."""
  await enforce_rate_limit("api_read")
  client = get_client()

  result = await client.search_speeches(query, limit=limit)

  raw_speeches = (
    result if isinstance(result, list) else result.get("speeches", result.get("results", []))
  )
  if not isinstance(raw_speeches, list):
    raw_speeches = []

  return [_parse_speech(s) for s in raw_speeches]
