// Database schema initialization for Notion skill
// Creates SQLite tables for pages, databases, users, and sync state
import './skill-state';

/**
 * Initialize Notion database schema
 */
export function initializeNotionSchema(): void {
  console.log('[notion] Initializing database schema...');

  // Pages table: metadata + extracted content
  db.exec(
    `CREATE TABLE IF NOT EXISTS pages (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      url TEXT,
      icon TEXT,
      parent_type TEXT NOT NULL,
      parent_id TEXT,
      created_by_id TEXT,
      last_edited_by_id TEXT,
      created_time TEXT NOT NULL,
      last_edited_time TEXT NOT NULL,
      archived INTEGER NOT NULL DEFAULT 0,
      content_text TEXT,
      content_synced_at INTEGER,
      synced_at INTEGER NOT NULL
    )`,
    []
  );

  // Databases table: metadata
  db.exec(
    `CREATE TABLE IF NOT EXISTS databases (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT,
      url TEXT,
      icon TEXT,
      property_count INTEGER NOT NULL DEFAULT 0,
      created_time TEXT NOT NULL,
      last_edited_time TEXT NOT NULL,
      archived INTEGER NOT NULL DEFAULT 0,
      synced_at INTEGER NOT NULL
    )`,
    []
  );

  // Users table
  db.exec(
    `CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      user_type TEXT NOT NULL,
      email TEXT,
      avatar_url TEXT,
      synced_at INTEGER NOT NULL
    )`,
    []
  );

  // Sync state key-value table
  db.exec(
    `CREATE TABLE IF NOT EXISTS sync_state (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at INTEGER NOT NULL DEFAULT 0
    )`,
    []
  );

  // Create indexes for performance
  db.exec('CREATE INDEX IF NOT EXISTS idx_pages_last_edited ON pages(last_edited_time DESC)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_pages_parent ON pages(parent_type, parent_id)', []);
  db.exec('CREATE INDEX IF NOT EXISTS idx_pages_archived ON pages(archived)', []);
  db.exec(
    'CREATE INDEX IF NOT EXISTS idx_databases_last_edited ON databases(last_edited_time DESC)',
    []
  );

  console.log('[notion] Database schema initialized successfully');
}

// Expose function on globalThis for use by main module
(globalThis as Record<string, unknown>).initializeNotionSchema = initializeNotionSchema;
