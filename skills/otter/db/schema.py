"""
SQLite schema definitions for Otter.ai data.

Database: data/otter.db
"""

from __future__ import annotations

SCHEMA_SQL = """
-- Speeches (meetings)
CREATE TABLE IF NOT EXISTS speeches (
    speech_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL DEFAULT 0,
    duration REAL NOT NULL DEFAULT 0,
    summary TEXT,
    speaker_count INTEGER NOT NULL DEFAULT 0,
    word_count INTEGER NOT NULL DEFAULT 0,
    folder_id TEXT,
    is_processed INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_speeches_created ON speeches(created_at DESC);

-- Transcript segments
CREATE TABLE IF NOT EXISTS transcript_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    speech_id TEXT NOT NULL REFERENCES speeches(speech_id),
    text TEXT NOT NULL DEFAULT '',
    start_offset REAL NOT NULL DEFAULT 0,
    end_offset REAL NOT NULL DEFAULT 0,
    speaker_id TEXT,
    speaker_name TEXT,
    segment_order INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_segments_speech ON transcript_segments(speech_id, segment_order);

-- Speakers
CREATE TABLE IF NOT EXISTS speakers (
    speaker_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    updated_at REAL NOT NULL
);

-- Periodic summaries
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_type TEXT NOT NULL,
    content TEXT NOT NULL,
    period_start REAL NOT NULL,
    period_end REAL NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_summaries_type_created ON summaries(summary_type, created_at DESC);
"""

PRAGMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
"""
