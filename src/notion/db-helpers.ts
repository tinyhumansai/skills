// Database helper functions for Notion skill
// CRUD operations for pages, databases, users, and sync state
import './skill-state';

// ---------------------------------------------------------------------------
// Types for database rows
// ---------------------------------------------------------------------------

export interface LocalPage {
  id: string;
  title: string;
  url: string | null;
  icon: string | null;
  parent_type: string;
  parent_id: string | null;
  created_by_id: string | null;
  last_edited_by_id: string | null;
  created_time: string;
  last_edited_time: string;
  archived: number;
  content_text: string | null;
  content_synced_at: number | null;
  synced_at: number;
}

export interface LocalDatabase {
  id: string;
  title: string;
  description: string | null;
  url: string | null;
  icon: string | null;
  property_count: number;
  created_time: string;
  last_edited_time: string;
  archived: number;
  synced_at: number;
}

export interface LocalUser {
  id: string;
  name: string;
  user_type: string;
  email: string | null;
  avatar_url: string | null;
  synced_at: number;
}

// ---------------------------------------------------------------------------
// Helper: Extract icon string from Notion icon object
// ---------------------------------------------------------------------------

function extractIcon(icon: unknown): string | null {
  if (!icon) return null;
  const iconObj = icon as Record<string, unknown>;
  if (iconObj.type === 'emoji') return iconObj.emoji as string;
  if (iconObj.type === 'external') return (iconObj.external as Record<string, string>)?.url || null;
  if (iconObj.type === 'file') return (iconObj.file as Record<string, string>)?.url || null;
  return null;
}

// ---------------------------------------------------------------------------
// Helper: Extract parent info from Notion parent object
// ---------------------------------------------------------------------------

function extractParent(parent: unknown): { type: string; id: string | null } {
  if (!parent) return { type: 'workspace', id: null };
  const p = parent as Record<string, unknown>;
  if (p.type === 'page_id') return { type: 'page_id', id: p.page_id as string };
  if (p.type === 'database_id') return { type: 'database_id', id: p.database_id as string };
  if (p.type === 'workspace') return { type: 'workspace', id: null };
  return { type: String(p.type || 'workspace'), id: null };
}

// ---------------------------------------------------------------------------
// Page operations
// ---------------------------------------------------------------------------

/**
 * Insert or update a page from a Notion API page object
 */
export function upsertPage(page: Record<string, unknown>): void {
  const now = Date.now();

  // Extract title from properties
  let title = page.id as string;
  const props = page.properties as Record<string, unknown> | undefined;
  if (props) {
    for (const key of Object.keys(props)) {
      const prop = props[key] as Record<string, unknown>;
      if (prop.type === 'title' && Array.isArray(prop.title)) {
        const texts = prop.title as Array<Record<string, unknown>>;
        const t = texts.map(rt => (rt.plain_text as string) || '').join('');
        if (t) {
          title = t;
          break;
        }
      }
    }
  }

  const iconStr = extractIcon(page.icon);
  const parent = extractParent(page.parent);
  const createdBy = page.created_by as Record<string, unknown> | undefined;
  const lastEditedBy = page.last_edited_by as Record<string, unknown> | undefined;

  db.exec(
    `INSERT OR REPLACE INTO pages (
      id, title, url, icon, parent_type, parent_id,
      created_by_id, last_edited_by_id,
      created_time, last_edited_time, archived,
      content_text, content_synced_at, synced_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
      COALESCE((SELECT content_text FROM pages WHERE id = ?), NULL),
      COALESCE((SELECT content_synced_at FROM pages WHERE id = ?), NULL),
      ?)`,
    [
      page.id as string,
      title,
      (page.url as string) || null,
      iconStr,
      parent.type,
      parent.id,
      (createdBy?.id as string) || null,
      (lastEditedBy?.id as string) || null,
      page.created_time as string,
      page.last_edited_time as string,
      (page.archived as boolean) ? 1 : 0,
      page.id as string, // for COALESCE subquery
      page.id as string, // for COALESCE subquery
      now,
    ]
  );
}

/**
 * Update a page's extracted content text
 */
export function updatePageContent(pageId: string, contentText: string): void {
  db.exec('UPDATE pages SET content_text = ?, content_synced_at = ? WHERE id = ?', [
    contentText,
    Date.now(),
    pageId,
  ]);
}

/**
 * Get a single page by ID
 */
export function getPageById(pageId: string): LocalPage | null {
  return db.get('SELECT * FROM pages WHERE id = ?', [pageId]) as LocalPage | null;
}

/**
 * Query local pages with optional search and filtering
 */
export function getLocalPages(
  options: { query?: string; limit?: number; includeArchived?: boolean } = {}
): LocalPage[] {
  let sql = 'SELECT * FROM pages WHERE 1=1';
  const params: unknown[] = [];

  if (!options.includeArchived) {
    sql += ' AND archived = 0';
  }

  if (options.query) {
    sql += ' AND (title LIKE ? OR content_text LIKE ?)';
    const term = `%${options.query}%`;
    params.push(term, term);
  }

  sql += ' ORDER BY last_edited_time DESC';

  const limit = options.limit || 50;
  sql += ' LIMIT ?';
  params.push(limit);

  return db.all(sql, params) as unknown as LocalPage[];
}

/**
 * Get pages that need content syncing (content not yet fetched, or stale)
 */
export function getPagesNeedingContent(limit: number): LocalPage[] {
  return db.all(
    `SELECT * FROM pages
     WHERE archived = 0
       AND (content_synced_at IS NULL OR content_synced_at < synced_at)
     ORDER BY last_edited_time DESC
     LIMIT ?`,
    [limit]
  ) as unknown as LocalPage[];
}

// ---------------------------------------------------------------------------
// Database operations
// ---------------------------------------------------------------------------

/**
 * Insert or update a database from a Notion API database object
 */
export function upsertDatabase(database: Record<string, unknown>): void {
  const now = Date.now();

  // Extract title
  let title = '(Untitled)';
  if (Array.isArray(database.title)) {
    const texts = database.title as Array<Record<string, unknown>>;
    const t = texts.map(rt => (rt.plain_text as string) || '').join('');
    if (t) title = t;
  }

  // Extract description
  let description: string | null = null;
  if (Array.isArray(database.description)) {
    const texts = database.description as Array<Record<string, unknown>>;
    const d = texts.map(rt => (rt.plain_text as string) || '').join('');
    if (d) description = d;
  }

  const iconStr = extractIcon(database.icon);
  const propertyCount = Object.keys((database.properties as Record<string, unknown>) || {}).length;

  db.exec(
    `INSERT OR REPLACE INTO databases (
      id, title, description, url, icon, property_count,
      created_time, last_edited_time, archived, synced_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      database.id as string,
      title,
      description,
      (database.url as string) || null,
      iconStr,
      propertyCount,
      database.created_time as string,
      database.last_edited_time as string,
      (database.archived as boolean) ? 1 : 0,
      now,
    ]
  );
}

/**
 * Query local databases with optional search
 */
export function getLocalDatabases(
  options: { query?: string; limit?: number } = {}
): LocalDatabase[] {
  let sql = 'SELECT * FROM databases WHERE archived = 0';
  const params: unknown[] = [];

  if (options.query) {
    sql += ' AND (title LIKE ? OR description LIKE ?)';
    const term = `%${options.query}%`;
    params.push(term, term);
  }

  sql += ' ORDER BY last_edited_time DESC';

  const limit = options.limit || 50;
  sql += ' LIMIT ?';
  params.push(limit);

  return db.all(sql, params) as unknown as LocalDatabase[];
}

// ---------------------------------------------------------------------------
// User operations
// ---------------------------------------------------------------------------

/**
 * Insert or update a user from a Notion API user object
 */
export function upsertUser(user: Record<string, unknown>): void {
  const now = Date.now();
  const person = user.person as Record<string, unknown> | undefined;

  db.exec(
    `INSERT OR REPLACE INTO users (
      id, name, user_type, email, avatar_url, synced_at
    ) VALUES (?, ?, ?, ?, ?, ?)`,
    [
      user.id as string,
      (user.name as string) || '(Unknown)',
      (user.type as string) || 'person',
      (person?.email as string) || null,
      (user.avatar_url as string) || null,
      now,
    ]
  );
}

/**
 * Get all local users
 */
export function getLocalUsers(): LocalUser[] {
  return db.all('SELECT * FROM users ORDER BY name', []) as unknown as LocalUser[];
}

// ---------------------------------------------------------------------------
// Sync state operations
// ---------------------------------------------------------------------------

/**
 * Get a sync state value by key
 */
export function getNotionSyncState(key: string): string | null {
  const row = db.get('SELECT value FROM sync_state WHERE key = ?', [key]) as {
    value: string;
  } | null;
  return row?.value || null;
}

/**
 * Set a sync state value
 */
export function setNotionSyncState(key: string, value: string): void {
  db.exec(
    `INSERT OR REPLACE INTO sync_state (key, value, updated_at)
     VALUES (?, ?, ?)`,
    [key, value, Date.now()]
  );
}

// ---------------------------------------------------------------------------
// Aggregate queries
// ---------------------------------------------------------------------------

/**
 * Get entity counts for status reporting
 */
export function getEntityCounts(): {
  pages: number;
  databases: number;
  users: number;
  pagesWithContent: number;
} {
  const pages = db.get('SELECT COUNT(*) as cnt FROM pages', []) as { cnt: number } | null;
  const databases = db.get('SELECT COUNT(*) as cnt FROM databases', []) as { cnt: number } | null;
  const users = db.get('SELECT COUNT(*) as cnt FROM users', []) as { cnt: number } | null;
  const pagesWithContent = db.get(
    'SELECT COUNT(*) as cnt FROM pages WHERE content_text IS NOT NULL',
    []
  ) as { cnt: number } | null;

  return {
    pages: pages?.cnt || 0,
    databases: databases?.cnt || 0,
    users: users?.cnt || 0,
    pagesWithContent: pagesWithContent?.cnt || 0,
  };
}

// ---------------------------------------------------------------------------
// Expose helper functions on globalThis for tools and sync to use
// ---------------------------------------------------------------------------

const _g = globalThis as Record<string, unknown>;
_g.upsertPage = upsertPage;
_g.upsertDatabase = upsertDatabase;
_g.upsertUser = upsertUser;
_g.updatePageContent = updatePageContent;
_g.getPageById = getPageById;
_g.getLocalPages = getLocalPages;
_g.getLocalDatabases = getLocalDatabases;
_g.getLocalUsers = getLocalUsers;
_g.getPagesNeedingContent = getPagesNeedingContent;
_g.getNotionSyncState = getNotionSyncState;
_g.setNotionSyncState = setNotionSyncState;
_g.getEntityCounts = getEntityCounts;
