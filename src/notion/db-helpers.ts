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
  page_entities: string | null;
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
 * Extract structured entities from Notion page properties and top-level fields.
 * Captures: created_by, last_edited_by, people properties (assignees),
 * relation properties (linked pages), created_by/last_edited_by property types.
 */
function extractPageEntities(
  page: Record<string, unknown>
): Array<{ id: string; type: string; name?: string; role: string; property?: string }> {
  const entities: Array<{
    id: string;
    type: string;
    name?: string;
    role: string;
    property?: string;
  }> = [];
  const seen = new Set<string>();

  const add = (
    id: string,
    type: string,
    name: string | undefined,
    role: string,
    property?: string
  ) => {
    const key = `${id}:${role}`;
    if (seen.has(key)) return;
    seen.add(key);
    entities.push({ id, type, name: name || undefined, role, property });
  };

  // Top-level created_by / last_edited_by
  const createdBy = page.created_by as Record<string, unknown> | undefined;
  if (createdBy?.id) {
    add(createdBy.id as string, 'person', createdBy.name as string | undefined, 'creator');
  }
  const lastEditedBy = page.last_edited_by as Record<string, unknown> | undefined;
  if (lastEditedBy?.id) {
    add(
      lastEditedBy.id as string,
      'person',
      lastEditedBy.name as string | undefined,
      'last_editor'
    );
  }

  // Scan properties for person, relation, created_by, last_edited_by types
  const props = page.properties as Record<string, unknown> | undefined;
  if (props) {
    for (const [propName, propVal] of Object.entries(props)) {
      const prop = propVal as Record<string, unknown>;
      const propType = prop.type as string;

      if (propType === 'people' && Array.isArray(prop.people)) {
        for (const person of prop.people as Array<Record<string, unknown>>) {
          if (person.id) {
            add(
              person.id as string,
              'person',
              person.name as string | undefined,
              'assignee',
              propName
            );
          }
        }
      } else if (propType === 'relation' && Array.isArray(prop.relation)) {
        for (const rel of prop.relation as Array<Record<string, unknown>>) {
          if (rel.id) {
            add(rel.id as string, 'page', undefined, 'linked', propName);
          }
        }
      } else if (propType === 'created_by' && prop.created_by) {
        const cb = prop.created_by as Record<string, unknown>;
        if (cb.id) {
          add(cb.id as string, 'person', cb.name as string | undefined, 'creator', propName);
        }
      } else if (propType === 'last_edited_by' && prop.last_edited_by) {
        const leb = prop.last_edited_by as Record<string, unknown>;
        if (leb.id) {
          add(leb.id as string, 'person', leb.name as string | undefined, 'last_editor', propName);
        }
      }
    }
  }

  return entities;
}

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

  // Extract structured entities from properties (people, relations, etc.)
  const pageEntities = extractPageEntities(page);
  const pageEntitiesJson = pageEntities.length > 0 ? JSON.stringify(pageEntities) : null;

  db.exec(
    `INSERT INTO pages (
      id, title, url, icon, parent_type, parent_id,
      created_by_id, last_edited_by_id,
      created_time, last_edited_time, archived, page_entities, synced_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
      title = excluded.title,
      url = excluded.url,
      icon = excluded.icon,
      parent_type = excluded.parent_type,
      parent_id = excluded.parent_id,
      created_by_id = excluded.created_by_id,
      last_edited_by_id = excluded.last_edited_by_id,
      created_time = excluded.created_time,
      last_edited_time = excluded.last_edited_time,
      archived = excluded.archived,
      page_entities = excluded.page_entities,
      synced_at = excluded.synced_at`,
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
      pageEntitiesJson,
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
 * Get pages that need content syncing (content not yet fetched, or stale).
 * Uses last_edited_time: only returns pages where we never synced content, or
 * the page was edited after we last synced (last_edited_time > content_synced_at).
 * @param limit - Max number of pages to return
 * @param updatedAfterIso - Optional ISO string cutoff; only return pages with last_edited_time >= this (e.g. 30 days ago)
 */
export function getPagesNeedingContent(limit: number, updatedAfterIso?: string): LocalPage[] {
  // last_edited_time is ISO string; content_synced_at is ms. Compare: need sync if
  // content_synced_at IS NULL or last_edited_time (as ms) > content_synced_at
  const lastEditedMsExpr = `(strftime('%s', substr(last_edited_time, 1, 10) || ' ' || substr(last_edited_time, 12, 8)) * 1000)`;
  let sql = `SELECT * FROM pages
     WHERE archived = 0
       AND (content_synced_at IS NULL OR content_synced_at < ${lastEditedMsExpr})`;
  const params: unknown[] = [];

  if (updatedAfterIso) {
    sql += ' AND last_edited_time >= ?';
    params.push(updatedAfterIso);
  }

  sql += ' ORDER BY last_edited_time DESC LIMIT ?';
  params.push(limit);

  return db.all(sql, params) as unknown as LocalPage[];
}

/**
 * Get structured entities for a page, with user names resolved from the users table.
 * Returns the stored page_entities with names filled in from local user records.
 */
export function getPageStructuredEntities(
  pageId: string
): Array<{ id: string; type: string; name?: string; role: string; property?: string }> {
  const page = db.get(
    'SELECT page_entities, created_by_id, last_edited_by_id FROM pages WHERE id = ?',
    [pageId]
  ) as {
    page_entities: string | null;
    created_by_id: string | null;
    last_edited_by_id: string | null;
  } | null;
  if (!page) return [];

  let entities: Array<{
    id: string;
    type: string;
    name?: string;
    role: string;
    property?: string;
  }> = [];
  if (page.page_entities) {
    try {
      entities = JSON.parse(page.page_entities);
    } catch {
      entities = [];
    }
  }

  // If no entities from properties, at least add created_by / last_edited_by
  const seen = new Set(entities.map(e => `${e.id}:${e.role}`));
  if (page.created_by_id && !seen.has(`${page.created_by_id}:creator`)) {
    entities.push({ id: page.created_by_id, type: 'person', role: 'creator' });
  }
  if (page.last_edited_by_id && !seen.has(`${page.last_edited_by_id}:last_editor`)) {
    entities.push({ id: page.last_edited_by_id, type: 'person', role: 'last_editor' });
  }

  // Resolve names from users table
  for (const entity of entities) {
    if (entity.type === 'person' && !entity.name) {
      const user = db.get('SELECT name FROM users WHERE id = ?', [entity.id]) as {
        name: string;
      } | null;
      if (user) entity.name = user.name;
    }
  }

  return entities;
}

/**
 * Get pages that need AI summarization.
 * Returns pages where content_text exists and no summary record exists
 * in the summaries table yet.
 */
export function getPagesNeedingSummary(limit: number): LocalPage[] {
  return db.all(
    `SELECT p.* FROM pages p
     LEFT JOIN summaries s ON s.page_id = p.id
     WHERE p.archived = 0
       AND p.content_text IS NOT NULL
       AND s.id IS NULL
     ORDER BY p.last_edited_time DESC
     LIMIT ?`,
    [limit]
  ) as unknown as LocalPage[];
}

// ---------------------------------------------------------------------------
// Summary operations
// ---------------------------------------------------------------------------

export interface LocalSummary {
  id: number;
  page_id: string;
  summary: string;
  category: string | null;
  sentiment: string | null;
  entities: string | null;
  topics: string | null;
  metadata: string | null;
  source_created_at: string;
  source_updated_at: string;
  created_at: number;
  synced: number;
  synced_at: number | null;
}

/**
 * Insert a new summary record for a page.
 * Entities, topics, and metadata are stored as JSON strings.
 */
export function insertSummary(opts: {
  pageId: string;
  summary: string;
  category?: string;
  sentiment?: string;
  entities?: unknown[];
  topics?: string[];
  metadata?: Record<string, unknown>;
  sourceCreatedAt: string;
  sourceUpdatedAt: string;
}): void {
  db.exec(
    `INSERT INTO summaries (
      page_id, summary, category, sentiment, entities, topics, metadata,
      source_created_at, source_updated_at, created_at, synced
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)`,
    [
      opts.pageId,
      opts.summary,
      opts.category || null,
      opts.sentiment || null,
      opts.entities ? JSON.stringify(opts.entities) : null,
      opts.topics ? JSON.stringify(opts.topics) : null,
      opts.metadata ? JSON.stringify(opts.metadata) : null,
      opts.sourceCreatedAt,
      opts.sourceUpdatedAt,
      Date.now(),
    ]
  );
}

/**
 * Get all summaries that have not been synced to the server yet.
 */
export function getUnsyncedSummaries(limit: number): LocalSummary[] {
  return db.all('SELECT * FROM summaries WHERE synced = 0 ORDER BY created_at ASC LIMIT ?', [
    limit,
  ]) as unknown as LocalSummary[];
}

/**
 * Mark a list of summary IDs as synced.
 */
export function markSummariesSynced(ids: number[]): void {
  if (ids.length === 0) return;
  const now = Date.now();
  const placeholders = ids.map(() => '?').join(',');
  db.exec(`UPDATE summaries SET synced = 1, synced_at = ? WHERE id IN (${placeholders})`, [
    now,
    ...ids,
  ]);
}

/**
 * Get count of synced vs unsynced summaries.
 */
export function getSummaryCounts(): { total: number; synced: number; pending: number } {
  const total = db.get('SELECT COUNT(*) as cnt FROM summaries', []) as { cnt: number } | null;
  const synced = db.get('SELECT COUNT(*) as cnt FROM summaries WHERE synced = 1', []) as {
    cnt: number;
  } | null;
  return {
    total: total?.cnt || 0,
    synced: synced?.cnt || 0,
    pending: (total?.cnt || 0) - (synced?.cnt || 0),
  };
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
 * Get a single database by ID
 */
export function getDatabaseById(databaseId: string): LocalDatabase | null {
  return db.get('SELECT * FROM databases WHERE id = ?', [databaseId]) as LocalDatabase | null;
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
  pagesWithSummary: number;
  summariesTotal: number;
  summariesPending: number;
} {
  const pages = db.get('SELECT COUNT(*) as cnt FROM pages', []) as { cnt: number } | null;
  const databases = db.get('SELECT COUNT(*) as cnt FROM databases', []) as { cnt: number } | null;
  const users = db.get('SELECT COUNT(*) as cnt FROM users', []) as { cnt: number } | null;
  const pagesWithContent = db.get(
    'SELECT COUNT(*) as cnt FROM pages WHERE content_text IS NOT NULL',
    []
  ) as { cnt: number } | null;
  const pagesWithSummary = db.get(
    'SELECT COUNT(DISTINCT page_id) as cnt FROM summaries',
    []
  ) as { cnt: number } | null;
  const summariesTotal = db.get('SELECT COUNT(*) as cnt FROM summaries', []) as {
    cnt: number;
  } | null;
  const summariesPending = db.get('SELECT COUNT(*) as cnt FROM summaries WHERE synced = 0', []) as {
    cnt: number;
  } | null;

  return {
    pages: pages?.cnt || 0,
    databases: databases?.cnt || 0,
    users: users?.cnt || 0,
    pagesWithContent: pagesWithContent?.cnt || 0,
    pagesWithSummary: pagesWithSummary?.cnt || 0,
    summariesTotal: summariesTotal?.cnt || 0,
    summariesPending: summariesPending?.cnt || 0,
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
_g.getDatabaseById = getDatabaseById;
_g.getLocalPages = getLocalPages;
_g.getLocalDatabases = getLocalDatabases;
_g.getLocalUsers = getLocalUsers;
_g.getPagesNeedingContent = getPagesNeedingContent;
_g.getPagesNeedingSummary = getPagesNeedingSummary;
_g.getPageStructuredEntities = getPageStructuredEntities;
_g.getNotionSyncState = getNotionSyncState;
_g.setNotionSyncState = setNotionSyncState;
_g.getEntityCounts = getEntityCounts;
_g.insertSummary = insertSummary;
_g.getUnsyncedSummaries = getUnsyncedSummaries;
_g.markSummariesSynced = markSummariesSynced;
_g.getSummaryCounts = getSummaryCounts;
