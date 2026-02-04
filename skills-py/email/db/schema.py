"""
SQLite schema definitions.

Database: data/email.db
"""

from __future__ import annotations

SCHEMA_SQL = """
-- Cached folder metadata
CREATE TABLE IF NOT EXISTS folders (
    account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    delimiter TEXT NOT NULL DEFAULT '/',
    flags TEXT NOT NULL DEFAULT '[]',
    total_messages INTEGER NOT NULL DEFAULT 0,
    unseen_messages INTEGER NOT NULL DEFAULT 0,
    uidvalidity INTEGER NOT NULL DEFAULT 0,
    uidnext INTEGER NOT NULL DEFAULT 0,
    last_synced REAL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (account_id, name)
);

-- Cached email headers + bodies
CREATE TABLE IF NOT EXISTS emails (
    account_id TEXT NOT NULL,
    folder TEXT NOT NULL,
    uid INTEGER NOT NULL,
    message_id_header TEXT,
    in_reply_to TEXT,
    references_header TEXT,
    thread_id TEXT,
    from_addr TEXT,
    from_name TEXT,
    to_addrs TEXT NOT NULL DEFAULT '[]',
    cc_addrs TEXT NOT NULL DEFAULT '[]',
    subject TEXT NOT NULL DEFAULT '',
    date REAL NOT NULL DEFAULT 0,
    body_text TEXT,
    body_html TEXT,
    body_preview TEXT NOT NULL DEFAULT '',
    fetched_body INTEGER NOT NULL DEFAULT 0,
    is_read INTEGER NOT NULL DEFAULT 0,
    is_flagged INTEGER NOT NULL DEFAULT 0,
    is_answered INTEGER NOT NULL DEFAULT 0,
    is_draft INTEGER NOT NULL DEFAULT 0,
    has_attachments INTEGER NOT NULL DEFAULT 0,
    attachment_count INTEGER NOT NULL DEFAULT 0,
    attachments_json TEXT NOT NULL DEFAULT '[]',
    raw_size INTEGER NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL,
    PRIMARY KEY (account_id, folder, uid)
);
CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date DESC);
CREATE INDEX IF NOT EXISTS idx_emails_thread ON emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_emails_msgid ON emails(message_id_header);
CREATE INDEX IF NOT EXISTS idx_emails_from ON emails(from_addr);
CREATE INDEX IF NOT EXISTS idx_emails_unread ON emails(is_read, folder);

-- Addresses seen in From/To/CC
CREATE TABLE IF NOT EXISTS contacts (
    email TEXT PRIMARY KEY,
    display_name TEXT,
    last_seen REAL NOT NULL DEFAULT 0,
    message_count INTEGER NOT NULL DEFAULT 0
);

-- Per-folder sync highwater marks
CREATE TABLE IF NOT EXISTS sync_state (
    account_id TEXT NOT NULL,
    folder TEXT NOT NULL,
    uidvalidity INTEGER NOT NULL DEFAULT 0,
    last_seen_uid INTEGER NOT NULL DEFAULT 0,
    last_full_sync REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (account_id, folder)
);

-- Periodic email activity summaries
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
