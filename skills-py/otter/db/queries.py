"""
Read/write query functions for the Otter.ai SQLite database.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
  import aiosqlite

  from ..state.types import OtterSpeaker, OtterSpeech, OtterTranscriptSegment

log = logging.getLogger("skill.otter.db.queries")


# ---------------------------------------------------------------------------
# Speeches
# ---------------------------------------------------------------------------


async def upsert_speech(db: aiosqlite.Connection, speech: OtterSpeech) -> None:
  await db.execute(
    """INSERT OR REPLACE INTO speeches
           (speech_id, title, created_at, duration, summary, speaker_count,
            word_count, folder_id, is_processed, raw_json, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (
      speech.speech_id,
      speech.title,
      speech.created_at,
      speech.duration,
      speech.summary,
      speech.speaker_count,
      speech.word_count,
      speech.folder_id,
      int(speech.is_processed),
      json.dumps(speech.raw_json) if speech.raw_json else None,
      time.time(),
    ),
  )


async def upsert_speeches_batch(db: aiosqlite.Connection, speeches: list[OtterSpeech]) -> None:
  for speech in speeches:
    await upsert_speech(db, speech)
  await db.commit()


async def get_all_speeches(db: aiosqlite.Connection, limit: int = 100) -> list[dict[str, Any]]:
  cursor = await db.execute("SELECT * FROM speeches ORDER BY created_at DESC LIMIT ?", (limit,))
  rows = await cursor.fetchall()
  return [dict(row) for row in rows]


async def get_speech_by_id(db: aiosqlite.Connection, speech_id: str) -> dict[str, Any] | None:
  cursor = await db.execute("SELECT * FROM speeches WHERE speech_id = ?", (speech_id,))
  row = await cursor.fetchone()
  return dict(row) if row else None


async def get_speech_ids(db: aiosqlite.Connection) -> set[str]:
  cursor = await db.execute("SELECT speech_id FROM speeches")
  rows = await cursor.fetchall()
  return {row[0] for row in rows}


# ---------------------------------------------------------------------------
# Transcript segments
# ---------------------------------------------------------------------------


async def upsert_transcript_segments(
  db: aiosqlite.Connection,
  speech_id: str,
  segments: list[OtterTranscriptSegment],
) -> None:
  # Clear existing segments for this speech
  await db.execute("DELETE FROM transcript_segments WHERE speech_id = ?", (speech_id,))
  for i, seg in enumerate(segments):
    await db.execute(
      """INSERT INTO transcript_segments
               (speech_id, text, start_offset, end_offset, speaker_id, speaker_name, segment_order)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
      (
        speech_id,
        seg.text,
        seg.start_offset,
        seg.end_offset,
        seg.speaker_id,
        seg.speaker_name,
        i,
      ),
    )
  await db.commit()


async def get_transcript_segments(db: aiosqlite.Connection, speech_id: str) -> list[dict[str, Any]]:
  cursor = await db.execute(
    "SELECT * FROM transcript_segments WHERE speech_id = ? ORDER BY segment_order",
    (speech_id,),
  )
  rows = await cursor.fetchall()
  return [dict(row) for row in rows]


async def search_transcript_segments(
  db: aiosqlite.Connection, speech_id: str, query: str
) -> list[dict[str, Any]]:
  cursor = await db.execute(
    """SELECT * FROM transcript_segments
           WHERE speech_id = ? AND text LIKE ?
           ORDER BY segment_order""",
    (speech_id, f"%{query}%"),
  )
  rows = await cursor.fetchall()
  return [dict(row) for row in rows]


async def search_all_transcripts(
  db: aiosqlite.Connection, query: str, limit: int = 50
) -> list[dict[str, Any]]:
  cursor = await db.execute(
    """SELECT ts.*, s.title as speech_title
           FROM transcript_segments ts
           JOIN speeches s ON ts.speech_id = s.speech_id
           WHERE ts.text LIKE ?
           ORDER BY s.created_at DESC
           LIMIT ?""",
    (f"%{query}%", limit),
  )
  rows = await cursor.fetchall()
  return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Speakers
# ---------------------------------------------------------------------------


async def upsert_speaker(db: aiosqlite.Connection, speaker: OtterSpeaker) -> None:
  await db.execute(
    """INSERT OR REPLACE INTO speakers
           (speaker_id, name, updated_at)
           VALUES (?, ?, ?)""",
    (speaker.speaker_id, speaker.name, time.time()),
  )


async def upsert_speakers_batch(db: aiosqlite.Connection, speakers: list[OtterSpeaker]) -> None:
  for speaker in speakers:
    await upsert_speaker(db, speaker)
  await db.commit()


async def get_all_speakers(db: aiosqlite.Connection) -> list[dict[str, Any]]:
  cursor = await db.execute("SELECT * FROM speakers ORDER BY name")
  rows = await cursor.fetchall()
  return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


async def insert_summary(
  db: aiosqlite.Connection,
  summary_type: str,
  content: Any,
  period_start: float,
  period_end: float,
) -> None:
  await db.execute(
    "INSERT INTO summaries (summary_type, content, period_start, period_end, created_at) VALUES (?, ?, ?, ?, ?)",
    (summary_type, json.dumps(content), period_start, period_end, time.time()),
  )
  await db.commit()


async def prune_old_data(db: aiosqlite.Connection) -> None:
  """Remove old summaries (>7 days)."""
  now = time.time()
  await db.execute("DELETE FROM summaries WHERE created_at < ?", (now - 604800,))
  await db.commit()
