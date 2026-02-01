"""
Otter.ai tool definitions (8 tools).
"""

from __future__ import annotations

TOOL_DEFINITIONS: list[tuple[str, str, dict]] = [
  (
    "list_meetings",
    "List recent Otter.ai meetings with titles, dates, and durations.",
    {
      "type": "object",
      "properties": {
        "limit": {
          "type": "number",
          "description": "Maximum number of meetings to return (default 20).",
          "default": 20,
        },
        "folder": {
          "type": "string",
          "description": "Optional folder ID to filter meetings.",
        },
      },
    },
  ),
  (
    "get_meeting",
    "Get the full transcript of an Otter.ai meeting by its speech ID.",
    {
      "type": "object",
      "properties": {
        "speech_id": {
          "type": "string",
          "description": "The speech/meeting ID.",
        },
      },
      "required": ["speech_id"],
    },
  ),
  (
    "get_meeting_summary",
    "Get the AI-generated summary of an Otter.ai meeting.",
    {
      "type": "object",
      "properties": {
        "speech_id": {
          "type": "string",
          "description": "The speech/meeting ID.",
        },
      },
      "required": ["speech_id"],
    },
  ),
  (
    "search_meetings",
    "Search across all Otter.ai meetings by keyword.",
    {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query string.",
        },
        "limit": {
          "type": "number",
          "description": "Maximum number of results (default 20).",
          "default": 20,
        },
      },
      "required": ["query"],
    },
  ),
  (
    "search_in_meeting",
    "Search within a specific Otter.ai meeting transcript.",
    {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query string.",
        },
        "speech_id": {
          "type": "string",
          "description": "The speech/meeting ID to search within.",
        },
      },
      "required": ["query", "speech_id"],
    },
  ),
  (
    "download_meeting_transcript",
    "Download the transcript of an Otter.ai meeting as plain text or SRT.",
    {
      "type": "object",
      "properties": {
        "speech_id": {
          "type": "string",
          "description": "The speech/meeting ID.",
        },
        "format": {
          "type": "string",
          "description": "Output format: 'txt' or 'srt' (default 'txt').",
          "enum": ["txt", "srt"],
          "default": "txt",
        },
      },
      "required": ["speech_id"],
    },
  ),
  (
    "get_otter_user",
    "Get the current Otter.ai user profile.",
    {
      "type": "object",
      "properties": {},
    },
  ),
  (
    "list_speakers",
    "List all recognized speakers in Otter.ai.",
    {
      "type": "object",
      "properties": {},
    },
  ),
]
