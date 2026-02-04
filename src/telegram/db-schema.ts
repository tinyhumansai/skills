// Database schema for Telegram skill persistent storage.
// Stores chats, messages, contacts, and sync state in SQLite.

/**
 * SQL schema for the Telegram skill.
 * All Telegram IDs are stored as TEXT because they are int64
 * which exceeds JavaScript's Number.MAX_SAFE_INTEGER.
 *
 * Each statement is in its own array element for separate execution.
 */
export const TELEGRAM_SCHEMA_STATEMENTS: string[] = [
  // Chat heads (from updateNewChat, updateChatPosition, etc.)
  `CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT,
    username TEXT,
    unread_count INTEGER DEFAULT 0,
    unread_mention_count INTEGER DEFAULT 0,
    last_message_id TEXT,
    last_message_date INTEGER,
    last_message_preview TEXT,
    order_position TEXT,
    is_pinned INTEGER DEFAULT 0,
    is_muted INTEGER DEFAULT 0,
    photo_small TEXT,
    member_count INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
  )`,

  // Messages
  `CREATE TABLE IF NOT EXISTS messages (
    id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    sender_id TEXT,
    sender_type TEXT,
    content_type TEXT NOT NULL,
    content_text TEXT,
    content_data TEXT,
    date INTEGER NOT NULL,
    edit_date INTEGER,
    reply_to_message_id TEXT,
    forward_info TEXT,
    is_outgoing INTEGER NOT NULL,
    is_pinned INTEGER DEFAULT 0,
    is_deleted INTEGER DEFAULT 0,
    views INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (chat_id, id)
  )`,

  // Contacts/Users
  `CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    phone_number TEXT,
    is_bot INTEGER DEFAULT 0,
    is_premium INTEGER DEFAULT 0,
    is_contact INTEGER DEFAULT 0,
    status TEXT,
    profile_photo_small TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
  )`,

  // Chat summaries (for AI context)
  `CREATE TABLE IF NOT EXISTS chat_summaries (
    chat_id TEXT PRIMARY KEY,
    summary_text TEXT,
    key_topics TEXT,
    message_count_analyzed INTEGER,
    last_message_id TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
  )`,

  // Sync state tracking
  `CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at INTEGER NOT NULL
  )`,

  // Indexes for efficient queries (SQLite doesn't support DESC in index definition)
  `CREATE INDEX IF NOT EXISTS idx_chats_order ON chats(order_position)`,
  `CREATE INDEX IF NOT EXISTS idx_chats_type ON chats(type)`,
  `CREATE INDEX IF NOT EXISTS idx_chats_updated ON chats(updated_at)`,
  `CREATE INDEX IF NOT EXISTS idx_messages_chat_date ON messages(chat_id, date)`,
  `CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)`,
  `CREATE INDEX IF NOT EXISTS idx_messages_content_type ON messages(content_type)`,
  `CREATE INDEX IF NOT EXISTS idx_contacts_username ON contacts(username)`,
  `CREATE INDEX IF NOT EXISTS idx_contacts_is_contact ON contacts(is_contact)`,
];

/**
 * Combined schema as single string (for backward compatibility).
 * @deprecated Use TELEGRAM_SCHEMA_STATEMENTS instead
 */
export const TELEGRAM_SCHEMA = TELEGRAM_SCHEMA_STATEMENTS.join(';\n') + ';';

/**
 * Legacy schema statements for backward compatibility.
 * The telegram_requests table was used in v1 but is no longer needed.
 */
export const LEGACY_SCHEMA_STATEMENTS: string[] = [
  `CREATE TABLE IF NOT EXISTS telegram_requests (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    args TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    result TEXT,
    error TEXT,
    created_at INTEGER NOT NULL,
    completed_at INTEGER
  )`,
  `CREATE INDEX IF NOT EXISTS idx_telegram_requests_status ON telegram_requests(status)`,
  `CREATE INDEX IF NOT EXISTS idx_telegram_requests_created ON telegram_requests(created_at)`,
];

/**
 * Combined legacy schema as single string (for backward compatibility).
 * @deprecated Use LEGACY_SCHEMA_STATEMENTS instead
 */
export const LEGACY_SCHEMA = LEGACY_SCHEMA_STATEMENTS.join(';\n') + ';';

// Extend globalThis type
declare global {
  function initializeTelegramSchema(): void;
}

/**
 * Execute all schema statements using the db bridge API.
 */
function initializeSchemaImpl(): void {
  const allStatements = [...TELEGRAM_SCHEMA_STATEMENTS, ...LEGACY_SCHEMA_STATEMENTS];
  for (const stmt of allStatements) {
    try {
      db.exec(stmt, []);
    } catch (err) {
      console.error('[telegram] Schema statement failed:', stmt.slice(0, 50), err);
    }
  }
}

// Expose on globalThis for reliable access across bundled modules
globalThis.initializeTelegramSchema = initializeSchemaImpl;

/**
 * Execute all schema statements using the db bridge API.
 * @deprecated Use globalThis.initializeTelegramSchema() instead
 */
export function initializeSchema(): void {
  initializeSchemaImpl();
}
