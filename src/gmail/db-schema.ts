// Database schema initialization for Gmail skill
// Creates SQLite tables for emails, threads, labels, and attachments
import './skill-state';

/**
 * Initialize Gmail database schema
 */
export function initializeGmailSchema(): void {
  console.log('[gmail] Initializing database schema...');

  // Emails table
  db.exec(
    `CREATE TABLE IF NOT EXISTS emails (
      id TEXT PRIMARY KEY,
      thread_id TEXT NOT NULL,
      subject TEXT NOT NULL,
      sender_email TEXT NOT NULL,
      sender_name TEXT,
      recipient_emails TEXT NOT NULL,
      cc_emails TEXT,
      bcc_emails TEXT,
      date INTEGER NOT NULL,
      snippet TEXT NOT NULL,
      body_text TEXT,
      body_html TEXT,
      is_read INTEGER NOT NULL DEFAULT 0,
      is_important INTEGER NOT NULL DEFAULT 0,
      is_starred INTEGER NOT NULL DEFAULT 0,
      has_attachments INTEGER NOT NULL DEFAULT 0,
      labels TEXT NOT NULL DEFAULT '[]',
      size_estimate INTEGER NOT NULL DEFAULT 0,
      history_id TEXT NOT NULL,
      internal_date TEXT NOT NULL,
      created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
      updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
    )`,
    []
  );

  // Threads table
  db.exec(
    `CREATE TABLE IF NOT EXISTS threads (
      id TEXT PRIMARY KEY,
      subject TEXT NOT NULL,
      snippet TEXT NOT NULL,
      message_count INTEGER NOT NULL DEFAULT 0,
      participants TEXT NOT NULL,
      last_message_date INTEGER NOT NULL,
      is_read INTEGER NOT NULL DEFAULT 0,
      has_attachments INTEGER NOT NULL DEFAULT 0,
      labels TEXT NOT NULL DEFAULT '[]',
      history_id TEXT NOT NULL,
      created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
      updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
    )`,
    []
  );

  // Labels table
  db.exec(
    `CREATE TABLE IF NOT EXISTS labels (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL UNIQUE,
      type TEXT NOT NULL,
      message_list_visibility TEXT NOT NULL,
      label_list_visibility TEXT NOT NULL,
      messages_total INTEGER NOT NULL DEFAULT 0,
      messages_unread INTEGER NOT NULL DEFAULT 0,
      threads_total INTEGER NOT NULL DEFAULT 0,
      threads_unread INTEGER NOT NULL DEFAULT 0,
      color_text TEXT,
      color_background TEXT,
      created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
      updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
    )`,
    []
  );

  // Attachments table
  db.exec(
    `CREATE TABLE IF NOT EXISTS attachments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      message_id TEXT NOT NULL,
      attachment_id TEXT NOT NULL,
      filename TEXT NOT NULL,
      mime_type TEXT NOT NULL,
      size INTEGER NOT NULL,
      part_id TEXT NOT NULL,
      created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
      FOREIGN KEY (message_id) REFERENCES emails (id) ON DELETE CASCADE
    )`,
    []
  );

  // Sync state table
  db.exec(
    `CREATE TABLE IF NOT EXISTS sync_state (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
    )`,
    []
  );

  // Create indexes for performance
  db.exec('CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails (thread_id)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_emails_date ON emails (date DESC)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails (sender_email)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_emails_labels ON emails (labels)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_emails_is_read ON emails (is_read)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_threads_date ON threads (last_message_date DESC)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_threads_labels ON threads (labels)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments (message_id)', []);

  console.log('[gmail] Database schema initialized successfully');
}

// Expose function on globalThis for use by main module
(globalThis as Record<string, unknown>).initializeGmailSchema = initializeGmailSchema;
