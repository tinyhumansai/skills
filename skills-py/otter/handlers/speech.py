"""
Speech/meeting domain tool handlers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..api import speech_api
from ..db import queries
from ..db.connection import get_db
from ..helpers import (
  ErrorCategory,
  ToolResult,
  format_duration,
  log_and_format_error,
  truncate_transcript,
)
from ..validation import opt_number, opt_string, req_string


async def list_meetings(args: dict[str, Any]) -> ToolResult:
  try:
    limit = opt_number(args, "limit", 20)
    folder = opt_string(args, "folder")

    speeches = await speech_api.fetch_speeches(limit=limit, folder=folder)
    if not speeches:
      return ToolResult(content="No meetings found.")

    lines = []
    for s in speeches:
      date_str = ""
      if s.created_at:
        date_str = datetime.fromtimestamp(s.created_at, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
      duration_str = format_duration(s.duration) if s.duration else "unknown"
      processed = "done" if s.is_processed else "processing"
      lines.append(
        f"[{s.speech_id}] {s.title or 'Untitled'} — {date_str} — {duration_str} — {processed}"
      )

    header = f"Found {len(speeches)} meeting(s):\n"
    return ToolResult(content=header + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("list_meetings", e, ErrorCategory.SPEECH)


async def get_meeting(args: dict[str, Any]) -> ToolResult:
  try:
    speech_id = req_string(args, "speech_id")

    # Fetch speech metadata
    speech = await speech_api.fetch_speech(speech_id)
    if not speech:
      return ToolResult(content=f"Meeting {speech_id} not found.", is_error=True)

    # Fetch transcript
    segments = await speech_api.fetch_transcript(speech_id)

    # Format output
    date_str = ""
    if speech.created_at:
      date_str = datetime.fromtimestamp(speech.created_at, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    duration_str = format_duration(speech.duration) if speech.duration else "unknown"

    header = (
      f"Meeting: {speech.title or 'Untitled'}\n"
      f"Date: {date_str}\n"
      f"Duration: {duration_str}\n"
      f"Speakers: {speech.speaker_count}\n"
      f"Words: {speech.word_count}\n"
    )

    if speech.summary:
      header += f"Summary: {speech.summary}\n"

    if segments:
      transcript_lines = []
      for seg in segments:
        speaker = f"[{seg.speaker_name}] " if seg.speaker_name else ""
        transcript_lines.append(f"{speaker}{seg.text}")
      transcript_text = "\n".join(transcript_lines)
      header += f"\n--- Transcript ---\n{truncate_transcript(transcript_text)}"
    else:
      header += "\n[No transcript available]"

    return ToolResult(content=header)
  except Exception as e:
    return log_and_format_error("get_meeting", e, ErrorCategory.SPEECH)


async def get_meeting_summary(args: dict[str, Any]) -> ToolResult:
  try:
    speech_id = req_string(args, "speech_id")

    speech = await speech_api.fetch_speech(speech_id)
    if not speech:
      return ToolResult(content=f"Meeting {speech_id} not found.", is_error=True)

    if speech.summary:
      return ToolResult(content=f'Summary for "{speech.title or "Untitled"}":\n\n{speech.summary}')

    # No summary in metadata — try to build one from transcript
    segments = await speech_api.fetch_transcript(speech_id)
    if not segments:
      return ToolResult(content=f"No summary or transcript available for meeting {speech_id}.")

    # Return first portion of transcript as a fallback
    transcript_lines = []
    for seg in segments[:20]:
      speaker = f"[{seg.speaker_name}] " if seg.speaker_name else ""
      transcript_lines.append(f"{speaker}{seg.text}")
    transcript_text = "\n".join(transcript_lines)

    return ToolResult(
      content=(
        f'No AI summary available for "{speech.title or "Untitled"}".\n\n'
        f"Transcript preview (first {len(transcript_lines)} segments):\n"
        f"{truncate_transcript(transcript_text)}"
      )
    )
  except Exception as e:
    return log_and_format_error("get_meeting_summary", e, ErrorCategory.SPEECH)


async def download_meeting_transcript(args: dict[str, Any]) -> ToolResult:
  try:
    speech_id = req_string(args, "speech_id")
    fmt = opt_string(args, "format") or "txt"

    if fmt not in ("txt", "srt"):
      return ToolResult(content="Format must be 'txt' or 'srt'.", is_error=True)

    # Try DB cache first
    try:
      db = await get_db()
      cached = await queries.get_transcript_segments(db, speech_id)
    except Exception:
      cached = []

    if not cached:
      segments = await speech_api.fetch_transcript(speech_id)
      if not segments:
        return ToolResult(content=f"No transcript available for meeting {speech_id}.")
      cached = [
        {
          "text": s.text,
          "start_offset": s.start_offset,
          "end_offset": s.end_offset,
          "speaker_name": s.speaker_name,
        }
        for s in segments
      ]

    if fmt == "srt":
      lines = []
      for i, seg in enumerate(cached, 1):
        start = _format_srt_time(seg.get("start_offset", 0))
        end = _format_srt_time(seg.get("end_offset", 0))
        text = seg.get("text", "")
        speaker = seg.get("speaker_name", "")
        prefix = f"[{speaker}] " if speaker else ""
        lines.append(f"{i}\n{start} --> {end}\n{prefix}{text}\n")
      content = "\n".join(lines)
    else:
      lines = []
      for seg in cached:
        speaker = seg.get("speaker_name", "")
        prefix = f"[{speaker}] " if speaker else ""
        lines.append(f"{prefix}{seg.get('text', '')}")
      content = "\n".join(lines)

    return ToolResult(content=truncate_transcript(content))
  except Exception as e:
    return log_and_format_error("download_meeting_transcript", e, ErrorCategory.TRANSCRIPT)


def _format_srt_time(seconds: float) -> str:
  """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
  hours = int(seconds // 3600)
  minutes = int((seconds % 3600) // 60)
  secs = int(seconds % 60)
  millis = int((seconds % 1) * 1000)
  return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
