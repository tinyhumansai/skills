// Database schema initialization for Gmail skill
// Creates SQLite tables for emails, threads, labels, and attachments
// All tables are scoped by credential_id to isolate data per integration.

/**
 * Initialize Gmail database schema
 */
export function initializeGmailSchema(): void {
  console.log('[gmail] Initializing database schema...');

  // Emails table
  db.exec(
    `CREATE TABLE IF NOT EXISTS emails (
      id TEXT NOT NULL,
      credential_id TEXT NOT NULL DEFAULT '',
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
      updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
      PRIMARY KEY (credential_id, id)
    )`,
    []
  );

  // Threads table
  db.exec(
    `CREATE TABLE IF NOT EXISTS threads (
      id TEXT NOT NULL,
      credential_id TEXT NOT NULL DEFAULT '',
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
      updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
      PRIMARY KEY (credential_id, id)
    )`,
    []
  );

  // Labels table
  db.exec(
    `CREATE TABLE IF NOT EXISTS labels (
      id TEXT NOT NULL,
      credential_id TEXT NOT NULL DEFAULT '',
      name TEXT NOT NULL,
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
      updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
      PRIMARY KEY (credential_id, id)
    )`,
    []
  );

  // Attachments table
  db.exec(
    `CREATE TABLE IF NOT EXISTS attachments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      credential_id TEXT NOT NULL DEFAULT '',
      message_id TEXT NOT NULL,
      attachment_id TEXT NOT NULL,
      filename TEXT NOT NULL,
      mime_type TEXT NOT NULL,
      size INTEGER NOT NULL,
      part_id TEXT NOT NULL,
      created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
      FOREIGN KEY (credential_id, message_id) REFERENCES emails (credential_id, id) ON DELETE CASCADE
    )`,
    []
  );

  // Create indexes for performance
  db.exec('CREATE INDEX IF NOT EXISTS idx_emails_cred ON emails (credential_id)', []);
  db.exec(
    'CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails (credential_id, thread_id)',
    []
  );
  db.exec('CREATE INDEX IF NOT EXISTS idx_emails_date ON emails (credential_id, date DESC)', []);
  db.exec(
    'CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails (credential_id, sender_email)',
    []
  );
  db.exec('CREATE INDEX IF NOT EXISTS idx_emails_labels ON emails (credential_id, labels)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_emails_is_read ON emails (credential_id, is_read)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_threads_cred ON threads (credential_id)', []);
  db.exec(
    'CREATE INDEX IF NOT EXISTS idx_threads_date ON threads (credential_id, last_message_date DESC)',
    []
  );
  db.exec('CREATE INDEX IF NOT EXISTS idx_threads_labels ON threads (credential_id, labels)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_attachments_cred ON attachments (credential_id)', []);
  db.exec(
    'CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments (credential_id, message_id)',
    []
  );

  // Migrations — safely add columns that may not exist on older schemas.
  const columns = db.all('PRAGMA table_info(emails)', []);
  const columnNames = new Set(columns.map(col => (col as { name: string }).name));

  if (!columnNames.has('backend_submitted')) {
    db.exec('ALTER TABLE emails ADD COLUMN backend_submitted INTEGER NOT NULL DEFAULT 0', []);
    db.exec(
      'CREATE INDEX IF NOT EXISTS idx_emails_backend_submitted ON emails (credential_id, backend_submitted)',
      []
    );
    console.log('[gmail] Added backend_submitted column to emails table');
  }

  if (!columnNames.has('is_sensitive')) {
    db.exec('ALTER TABLE emails ADD COLUMN is_sensitive INTEGER NOT NULL DEFAULT 0', []);
    db.exec(
      'CREATE INDEX IF NOT EXISTS idx_emails_is_sensitive ON emails (credential_id, is_sensitive)',
      []
    );
    console.log('[gmail] Added is_sensitive column to emails table');
  }

  // Migration: add credential_id to existing tables that lack it
  if (!columnNames.has('credential_id')) {
    db.exec("ALTER TABLE emails ADD COLUMN credential_id TEXT NOT NULL DEFAULT ''", []);
    db.exec('CREATE INDEX IF NOT EXISTS idx_emails_cred ON emails (credential_id)', []);

    const threadCols = db.all('PRAGMA table_info(threads)', []);
    const threadColNames = new Set(threadCols.map(col => (col as { name: string }).name));
    if (!threadColNames.has('credential_id')) {
      db.exec("ALTER TABLE threads ADD COLUMN credential_id TEXT NOT NULL DEFAULT ''", []);
      db.exec('CREATE INDEX IF NOT EXISTS idx_threads_cred ON threads (credential_id)', []);
    }

    const labelCols = db.all('PRAGMA table_info(labels)', []);
    const labelColNames = new Set(labelCols.map(col => (col as { name: string }).name));
    if (!labelColNames.has('credential_id')) {
      db.exec("ALTER TABLE labels ADD COLUMN credential_id TEXT NOT NULL DEFAULT ''", []);
    }

    const attCols = db.all('PRAGMA table_info(attachments)', []);
    const attColNames = new Set(attCols.map(col => (col as { name: string }).name));
    if (!attColNames.has('credential_id')) {
      db.exec("ALTER TABLE attachments ADD COLUMN credential_id TEXT NOT NULL DEFAULT ''", []);
      db.exec('CREATE INDEX IF NOT EXISTS idx_attachments_cred ON attachments (credential_id)', []);
    }

    console.log('[gmail] Added credential_id column to all tables');
  }

  console.log('[gmail] Database schema initialized successfully');
}
