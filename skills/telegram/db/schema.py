"""
SQLite schema definitions and migrations.

Database: data/telegram.db
"""

from __future__ import annotations

SCHEMA_SQL = """
-- Connection/auth state (single row)
CREATE TABLE IF NOT EXISTS skill_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);

-- Users cache
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT,
    username TEXT,
    phone_number TEXT,
    is_bot INTEGER NOT NULL DEFAULT 0,
    is_verified INTEGER,
    is_premium INTEGER,
    access_hash TEXT,
    updated_at REAL NOT NULL
);

-- Chats cache
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    title TEXT,
    type TEXT NOT NULL,
    username TEXT,
    access_hash TEXT,
    unread_count INTEGER NOT NULL DEFAULT 0,
    is_pinned INTEGER NOT NULL DEFAULT 0,
    participants_count INTEGER,
    last_message_id TEXT,
    last_message_date REAL,
    sort_order INTEGER,
    updated_at REAL NOT NULL
);

-- Messages cache
CREATE TABLE IF NOT EXISTS messages (
    id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    date REAL NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    from_id TEXT,
    from_name TEXT,
    is_outgoing INTEGER NOT NULL DEFAULT 0,
    is_edited INTEGER NOT NULL DEFAULT 0,
    is_forwarded INTEGER NOT NULL DEFAULT 0,
    reply_to_message_id TEXT,
    thread_id TEXT,
    media_type TEXT,
    views INTEGER,
    updated_at REAL NOT NULL,
    PRIMARY KEY (chat_id, id)
);
CREATE INDEX IF NOT EXISTS idx_messages_chat_date ON messages(chat_id, date DESC);

-- Periodic summaries (generated every 20 minutes)
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_type TEXT NOT NULL,
    content TEXT NOT NULL,
    period_start REAL NOT NULL,
    period_end REAL NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_summaries_type_created ON summaries(summary_type, created_at DESC);

-- Events log
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    chat_id TEXT,
    data TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_type_created ON events(event_type, created_at DESC);
"""

PRAGMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
"""
