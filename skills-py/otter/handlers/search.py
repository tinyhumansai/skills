"""
Search domain tool handlers.
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
from ..validation import opt_number, req_string


async def search_meetings(args: dict[str, Any]) -> ToolResult:
  try:
    query = req_string(args, "query")
    limit = opt_number(args, "limit", 20)

    # Try API search first
    try:
      speeches = await speech_api.search_speeches(query, limit=limit)
    except Exception:
      speeches = []

    # Fall back to DB search if API search fails or returns nothing
    if not speeches:
      try:
        db = await get_db()
        rows = await queries.search_all_transcripts(db, query, limit=limit)
        if rows:
          # Group by speech
          seen: dict[str, list[str]] = {}
          speech_titles: dict[str, str] = {}
          for row in rows:
            sid = row.get("speech_id", "")
            text = row.get("text", "")
            speech_titles[sid] = row.get("speech_title", "Untitled")
            if sid not in seen:
              seen[sid] = []
            seen[sid].append(text)

          lines = []
          for sid, excerpts in seen.items():
            title = speech_titles.get(sid, "Untitled")
            excerpt_preview = " ... ".join(excerpts[:3])
            if len(excerpt_preview) > 200:
              excerpt_preview = excerpt_preview[:200] + "..."
            lines.append(f"[{sid}] {title}: {excerpt_preview}")

          return ToolResult(
            content=f"Found matches in {len(seen)} meeting(s) (from cache):\n" + "\n".join(lines)
          )
      except Exception:
        pass
      return ToolResult(content=f'No results found for "{query}".')

    lines = []
    for s in speeches:
      date_str = ""
      if s.created_at:
        date_str = datetime.fromtimestamp(s.created_at, tz=UTC).strftime("%Y-%m-%d")
      duration_str = format_duration(s.duration) if s.duration else ""
      lines.append(f"[{s.speech_id}] {s.title or 'Untitled'} — {date_str} — {duration_str}")

    return ToolResult(content=f"Found {len(speeches)} meeting(s):\n" + "\n".join(lines))
  except Exception as e:
    return log_and_format_error("search_meetings", e, ErrorCategory.SEARCH)


async def search_in_meeting(args: dict[str, Any]) -> ToolResult:
  try:
    query = req_string(args, "query")
    speech_id = req_string(args, "speech_id")

    # Try DB cache first
    try:
      db = await get_db()
      rows = await queries.search_transcript_segments(db, speech_id, query)
    except Exception:
      rows = []

    if not rows:
      # Fetch transcript from API and search locally
      segments = await speech_api.fetch_transcript(speech_id)
      query_lower = query.lower()
      matching = [s for s in segments if query_lower in s.text.lower()]
      if not matching:
        return ToolResult(content=f'No matches for "{query}" in meeting {speech_id}.')

      lines = []
      for seg in matching:
        speaker = f"[{seg.speaker_name}] " if seg.speaker_name else ""
        time_str = format_duration(seg.start_offset) if seg.start_offset else ""
        lines.append(f"{time_str} {speaker}{seg.text}")

      return ToolResult(
        content=f'Found {len(matching)} match(es) for "{query}":\n'
        + truncate_transcript("\n".join(lines))
      )

    # Format cached results
    lines = []
    for row in rows:
      speaker = row.get("speaker_name", "")
      prefix = f"[{speaker}] " if speaker else ""
      time_str = format_duration(row.get("start_offset", 0))
      lines.append(f"{time_str} {prefix}{row.get('text', '')}")

    return ToolResult(
      content=f'Found {len(rows)} match(es) for "{query}" in meeting {speech_id}:\n'
      + truncate_transcript("\n".join(lines))
    )
  except Exception as e:
    return log_and_format_error("search_in_meeting", e, ErrorCategory.SEARCH)
