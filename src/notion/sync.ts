// Notion sync engine
// Periodically downloads pages, databases, users, and page content from Notion
// into local SQLite for fast local querying.
import type { NotionApi } from './api/index';
import './skill-state';
import type { NotionGlobals } from './types';

// Resolve helpers and API from globalThis at call time.
// We avoid module imports of n()/getApi() because esbuild's IIFE bundling
// can fail to resolve peer-module exports in sync.ts (tools/ works fine
// because they're in a subdirectory). Resolving from globalThis is reliable.
const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

const getApi = (): NotionApi => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionApi === 'object') {
    return (g.exports as Record<string, unknown>).notionApi as NotionApi;
  }
  return g.notionApi as NotionApi;
};

// ---------------------------------------------------------------------------
// Main sync orchestrator
// ---------------------------------------------------------------------------

export function performSync(): void {
  const s = globalThis.getNotionSkillState();

  // Guard: skip if already syncing or no credential
  if (s.syncStatus.syncInProgress) {
    console.log('[notion] Sync already in progress, skipping');
    return;
  }

  if (!oauth.getCredential()) {
    console.log('[notion] No credential, skipping sync');
    return;
  }

  const startTime = Date.now();
  s.syncStatus.syncInProgress = true;
  s.syncStatus.lastSyncError = null;
  publishSyncState();

  try {
    // Phase 1: Sync users
    console.log('[notion] Sync phase 1: users');
    syncUsers();

    // Phase 2: Sync pages and databases via search
    console.log('[notion] Sync phase 2: pages & databases');
    syncSearchItems();

    // Phase 3: Sync page content (block text)
    if (s.config.contentSyncEnabled) {
      console.log('[notion] Sync phase 3: page content');
      syncContent();
    }

    // Phase 4a: Generate AI summaries (stored locally, not yet synced)
    if (s.config.contentSyncEnabled) {
      console.log('[notion] Sync phase 4a: generate AI summaries');
      generateSummaries();
    }

    // Phase 4b: Sync unsynced summaries to the server
    console.log('[notion] Sync phase 4b: sync summaries to server');
    syncSummariesToServer();

    // Update sync state
    const durationMs = Date.now() - startTime;
    const nowMs = Date.now();
    s.syncStatus.nextSyncTime = nowMs + s.config.syncIntervalMinutes * 60 * 1000;
    s.syncStatus.lastSyncDurationMs = durationMs;

    // Persist sync time in database
    const { getEntityCounts } = n();

    // Only advance lastSyncTime if we actually have items in the DB.
    // This prevents the incremental sync from skipping everything on the
    // next run if the first sync stored 0 items (e.g. due to errors).
    const counts = getEntityCounts();
    if (counts.pages > 0 || counts.databases > 0) {
      s.syncStatus.lastSyncTime = nowMs;
      store.set('last_sync_time', s.syncStatus.lastSyncTime);
    }

    // Update counts
    s.syncStatus.totalPages = counts.pages;
    s.syncStatus.totalDatabases = counts.databases;
    s.syncStatus.totalUsers = counts.users;
    s.syncStatus.pagesWithContent = counts.pagesWithContent;
    s.syncStatus.pagesWithSummary = counts.pagesWithSummary;
    s.syncStatus.summariesTotal = counts.summariesTotal;
    s.syncStatus.summariesPending = counts.summariesPending;

    console.log(
      `[notion] Sync complete in ${durationMs}ms — ${counts.pages} pages, ${counts.databases} databases, ${counts.users} users`
    );
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    s.syncStatus.lastSyncError = errorMsg;
    s.syncStatus.lastSyncDurationMs = Date.now() - startTime;
    console.error(`[notion] Sync failed: ${errorMsg}`);
  } finally {
    s.syncStatus.syncInProgress = false;
    publishSyncState();
  }
}

// ---------------------------------------------------------------------------
// Phase 1: Sync users
// ---------------------------------------------------------------------------

function syncUsers(): void {
  const upsertUser = (globalThis as Record<string, unknown>).upsertUser as
    | ((user: Record<string, unknown>) => void)
    | undefined;
  if (!upsertUser) {
    console.warn('[notion] upsertUser not available on globalThis — skipping user sync');
    return;
  }

  let startCursor: string | undefined;
  let hasMore = true;
  let count = 0;

  while (hasMore) {
    const result = getApi().listUsers(100, startCursor);

    for (const user of result.results) {
      try {
        upsertUser(user as Record<string, unknown>);
        count++;
      } catch (e) {
        console.error(
          `[notion] Failed to upsert user ${(user as Record<string, unknown>).id}: ${e}`
        );
      }
    }

    hasMore = result.has_more;
    startCursor = (result.next_cursor as string | undefined) || undefined;
  }

  console.log(`[notion] Synced ${count} users`);
}

// ---------------------------------------------------------------------------
// Phase 2: Sync pages and databases via search (incremental)
// Restricts to items updated in the last 30 days to limit data volume.
// ---------------------------------------------------------------------------

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

function syncSearchItems(): void {
  const api = getApi();
  const upsertPage = (globalThis as Record<string, unknown>).upsertPage as
    | ((page: Record<string, unknown>) => void)
    | undefined;
  const upsertDatabase = (globalThis as Record<string, unknown>).upsertDatabase as
    | ((database: Record<string, unknown>) => void)
    | undefined;
  const getPageById = (globalThis as Record<string, unknown>).getPageById as
    | ((id: string) => { last_edited_time: string } | null)
    | undefined;
  const getDatabaseById = (globalThis as Record<string, unknown>).getDatabaseById as
    | ((id: string) => { last_edited_time: string } | null)
    | undefined;

  if (!upsertPage || !upsertDatabase) {
    console.warn(
      '[notion] upsertPage/upsertDatabase not available on globalThis — skipping search sync'
    );
    return;
  }

  const lastSyncTime = (store.get('last_sync_time') as number | null) || 0;
  const isFirstSync = lastSyncTime === 0;
  const cutoffMs = Date.now() - THIRTY_DAYS_MS;

  let startCursor: string | undefined;
  let hasMore = true;
  let pageCount = 0;
  let dbCount = 0;
  let pageSkipped = 0;
  let dbSkipped = 0;
  let errorCount = 0;
  let reachedOldItems = false;

  while (hasMore && !reachedOldItems) {
    const body: Record<string, unknown> = {
      page_size: 100,
      sort: { direction: 'descending', timestamp: 'last_edited_time' },
    };
    if (startCursor) body.start_cursor = startCursor;

    const result = api.search(body);

    for (const item of result.results) {
      const rec = item as Record<string, unknown>;
      const lastEdited = rec.last_edited_time as string;
      if (!lastEdited) continue; // Skip partial objects without timestamps

      const editedMs = new Date(lastEdited).getTime();

      // Restrict to items updated in the last 30 days
      if (editedMs < cutoffMs) {
        reachedOldItems = true;
        break;
      }

      // Incremental: stop when we reach items older than last sync
      if (!isFirstSync && editedMs <= lastSyncTime) {
        reachedOldItems = true;
        break;
      }

      const objectType = rec.object as string;

      if (objectType === 'page') {
        const existing = getPageById?.(rec.id as string);
        if (existing && existing.last_edited_time === lastEdited) {
          pageSkipped++;
        } else {
          try {
            upsertPage(rec);
            pageCount++;
          } catch (e) {
            console.error(`[notion] Failed to upsert page ${rec.id}: ${e}`);
            errorCount++;
          }
        }
      } else if (objectType === 'data_source' || objectType === 'database') {
        const existing = getDatabaseById?.(rec.id as string);
        if (existing && existing.last_edited_time === lastEdited) {
          dbSkipped++;
        } else {
          try {
            upsertDatabase(rec);
            dbCount++;
          } catch (e) {
            console.error(`[notion] Failed to upsert database ${rec.id}: ${e}`);
            errorCount++;
          }
        }
      } else {
        console.log(`[notion] Unknown object type in search results: ${objectType}`);
      }
    }

    hasMore = result.has_more;
    startCursor = (result.next_cursor as string | undefined) || undefined;
  }

  // Explicitly fetch data_sources (API 2025-09-03: unfiltered search may not return them)
  const dsResult = syncDataSources(
    upsertDatabase,
    getDatabaseById,
    cutoffMs,
    lastSyncTime,
    isFirstSync
  );
  dbCount += dsResult.count;
  dbSkipped += dsResult.skipped;
  errorCount += dsResult.errors;

  // Record that sync happened (even if first sync was partial)
  store.set('last_search_sync', Date.now());

  const skipMsg =
    pageSkipped > 0 || dbSkipped > 0 ? ` (${pageSkipped} pages, ${dbSkipped} dbs unchanged)` : '';
  const errorMsg = errorCount > 0 ? `, ${errorCount} errors` : '';
  console.log(
    `[notion] Synced ${pageCount} pages, ${dbCount} databases (last 30 days)${skipMsg}${errorMsg}`
  );
}

function syncDataSources(
  upsertDatabase: (db: Record<string, unknown>) => void,
  getDatabaseById: ((id: string) => { last_edited_time: string } | null) | undefined,
  cutoffMs: number,
  lastSyncTime: number,
  isFirstSync: boolean
): { count: number; skipped: number; errors: number } {
  const api = getApi();
  let startCursor: string | undefined;
  let hasMore = true;
  let count = 0;
  let skipped = 0;
  let errors = 0;
  let reachedOldItems = false;

  while (hasMore && !reachedOldItems) {
    const result = api.search({
      page_size: 100,
      sort: { direction: 'descending', timestamp: 'last_edited_time' },
      filter: { property: 'object', value: 'data_source' },
      ...(startCursor ? { start_cursor: startCursor } : {}),
    });

    for (const item of result.results) {
      const rec = item as Record<string, unknown>;
      const lastEdited = rec.last_edited_time as string;
      if (!lastEdited) continue;

      const editedMs = new Date(lastEdited).getTime();

      if (editedMs < cutoffMs) {
        reachedOldItems = true;
        break;
      }
      if (!isFirstSync && editedMs <= lastSyncTime) {
        reachedOldItems = true;
        break;
      }

      const existing = getDatabaseById?.(rec.id as string);
      if (existing && existing.last_edited_time === lastEdited) {
        skipped++;
      } else {
        try {
          upsertDatabase(rec);
          count++;
        } catch (e) {
          console.error(`[notion] Failed to upsert data_source ${rec.id}: ${e}`);
          errors++;
        }
      }
    }

    hasMore = result.has_more;
    startCursor = (result.next_cursor as string | undefined) || undefined;
  }

  return { count, skipped, errors };
}

// ---------------------------------------------------------------------------
// Phase 3: Sync page content (block text extraction)
// ---------------------------------------------------------------------------

function syncContent(): void {
  const s = globalThis.getNotionSkillState();
  const { fetchBlockTreeText } = n();
  const getPagesNeedingContent = (globalThis as Record<string, unknown>).getPagesNeedingContent as
    | ((limit: number, updatedAfterIso?: string) => Array<{ id: string; title: string }>)
    | undefined;
  const updatePageContent = (globalThis as Record<string, unknown>).updatePageContent as
    | ((pageId: string, text: string) => void)
    | undefined;

  if (!getPagesNeedingContent || !updatePageContent) return;

  const batchSize = s.config.maxPagesPerContentSync;
  const cutoffIso = new Date(Date.now() - THIRTY_DAYS_MS).toISOString();
  const pages = getPagesNeedingContent(batchSize, cutoffIso);
  let synced = 0;
  let failed = 0;

  for (const page of pages) {
    try {
      const text = fetchBlockTreeText(page.id, 2);
      updatePageContent(page.id, text);
      synced++;
    } catch (e) {
      // Individual page failures are logged but don't abort the batch
      console.error(`[notion] Failed to sync content for page ${page.id}: ${e}`);
      failed++;
    }
  }

  console.log(
    `[notion] Content sync: ${synced} pages updated${failed > 0 ? `, ${failed} failed` : ''}`
  );
}

// ---------------------------------------------------------------------------
// Phase 4: AI summarization of synced page content
// ---------------------------------------------------------------------------

const VALID_CATEGORIES = [
  'research',
  'meeting_notes',
  'project',
  'documentation',
  'planning',
  'design',
  'engineering',
  'marketing',
  'finance',
  'hr',
  'legal',
  'operations',
  'other',
] as const;
const VALID_SENTIMENTS = ['positive', 'neutral', 'negative', 'mixed'] as const;
const VALID_ENTITY_TYPES = [
  'person',
  'wallet',
  'channel',
  'group',
  'organization',
  'token',
  'other',
] as const;

interface PageClassification {
  category: string;
  sentiment: string;
  entities: Array<{ id: string; type: string; name?: string; role?: string }>;
  topics: string[];
}

/**
 * Use the local LLM to infer category, sentiment, entities, and topics in one call.
 * Returns defaults on failure so callers always get usable values.
 */
function inferClassification(text: string): PageClassification {
  const defaults: PageClassification = {
    category: 'other',
    sentiment: 'neutral',
    entities: [],
    topics: [],
  };
  try {
    const prompt =
      `Analyze the following Notion page. Respond with ONLY a JSON object:\n` +
      `- "category": one of [${VALID_CATEGORIES.join(', ')}]\n` +
      `- "sentiment": one of [${VALID_SENTIMENTS.join(', ')}]\n` +
      `- "entities": array of {id, type, name, role} where type is one of [${VALID_ENTITY_TYPES.join(', ')}]. ` +
      `Extract people mentioned, referenced pages, organizations, tokens/coins, wallets, channels, or groups.\n` +
      `- "topics": array of short bullet-point strings (3-7 key topics or takeaways)\n\n` +
      `${text}`;
    const raw = model.generate(prompt, { maxTokens: 500, temperature: 0.1 });
    const match = raw.match(/\{[\s\S]*\}/);
    if (match) {
      const parsed = JSON.parse(match[0]) as Partial<PageClassification>;

      const category = VALID_CATEGORIES.includes(
        parsed.category as (typeof VALID_CATEGORIES)[number]
      )
        ? parsed.category!
        : 'other';
      const sentiment = VALID_SENTIMENTS.includes(
        parsed.sentiment as (typeof VALID_SENTIMENTS)[number]
      )
        ? parsed.sentiment!
        : 'neutral';

      // Validate entities array
      const entities: PageClassification['entities'] = [];
      if (Array.isArray(parsed.entities)) {
        for (const e of parsed.entities) {
          const ent = e as Record<string, unknown>;
          if (ent.id || ent.name) {
            entities.push({
              id: String(ent.id || ent.name || ''),
              type: VALID_ENTITY_TYPES.includes(
                String(ent.type || '') as (typeof VALID_ENTITY_TYPES)[number]
              )
                ? String(ent.type)
                : 'other',
              name: ent.name ? String(ent.name) : undefined,
              role: ent.role ? String(ent.role) : undefined,
            });
          }
        }
      }

      // Validate topics array
      const topics: string[] = [];
      if (Array.isArray(parsed.topics)) {
        for (const t of parsed.topics) {
          if (typeof t === 'string' && t.trim()) topics.push(t.trim());
        }
      }

      return { category, sentiment, entities, topics };
    }
  } catch {
    // Fall through to defaults
  }
  return defaults;
}

const CONTENT_LIMITS = [3000, 1500, 500];

/**
 * Attempt summarization with progressively smaller content chunks.
 * Local models have limited context windows; retry with less text on overflow.
 */
function summarizeWithFallback(content: string, metaBlock: string): string | null {
  const instruction =
    'Write a 2-3 sentence summary of this Notion page. Be direct and dense — include all key facts, decisions, names, dates, and action items. Omit filler and pleasantries.';

  for (const limit of CONTENT_LIMITS) {
    const truncated =
      content.length > limit ? content.substring(0, limit) + '\n...(truncated)' : content;
    const prompt = `${instruction}\n\n--- Page Metadata ---\n${metaBlock}\n\n--- Page Content ---\n${truncated}`;
    try {
      const result = model.summarize(prompt, { maxTokens: 10000 });
      if (result && result.trim()) return result.trim();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      // Context overflow — retry with less content
      if (
        msg.includes('No sequences left') ||
        msg.includes('context') ||
        msg.includes('too long')
      ) {
        continue;
      }
      throw e; // Re-throw non-context errors
    }
  }
  return null;
}

/**
 * Merge structured entities (from Notion properties) with LLM-inferred entities.
 * Structured entities take priority (they have verified IDs from the API).
 * LLM entities are added if they don't duplicate an existing id+role pair.
 */
function mergeEntities(
  structured: Array<{ id: string; type: string; name?: string; role: string; property?: string }>,
  llmInferred: Array<{ id: string; type: string; name?: string; role?: string }>
): Array<{ id: string; type: string; name?: string; role: string; property?: string }> {
  const merged = [...structured];
  const seen = new Set(structured.map(e => e.id.toLowerCase()));

  for (const e of llmInferred) {
    if (!seen.has(e.id.toLowerCase())) {
      seen.add(e.id.toLowerCase());
      merged.push({ id: e.id, type: e.type, name: e.name, role: e.role || 'mentioned' });
    }
  }

  return merged;
}

/**
 * Phase 4a: Generate AI summaries for pages that need them.
 * Stores results in the `summaries` table with synced=0.
 * Does NOT submit to the server — that's handled by syncSummariesToServer().
 */
function generateSummaries(): void {
  const s = globalThis.getNotionSkillState();

  // Check if the local model is available
  if (!model.isAvailable()) {
    console.log('[notion] AI model not available — skipping summaries');
    return;
  }

  const getPagesNeedingSummary = (globalThis as Record<string, unknown>).getPagesNeedingSummary as
    | ((
        limit: number
      ) => Array<{
        id: string;
        title: string;
        content_text: string;
        url: string | null;
        last_edited_time: string;
        created_time: string;
      }>)
    | undefined;
  const getPageStructuredEntities = (globalThis as Record<string, unknown>)
    .getPageStructuredEntities as
    | ((
        pageId: string
      ) => Array<{ id: string; type: string; name?: string; role: string; property?: string }>)
    | undefined;
  const insertSummaryFn = (globalThis as Record<string, unknown>).insertSummary as
    | ((opts: {
        pageId: string;
        summary: string;
        category?: string;
        sentiment?: string;
        entities?: unknown[];
        topics?: string[];
        metadata?: Record<string, unknown>;
        sourceCreatedAt: string;
        sourceUpdatedAt: string;
      }) => void)
    | undefined;

  if (!getPagesNeedingSummary || !insertSummaryFn) return;

  const batchSize = s.config.maxPagesPerContentSync;
  const pages = getPagesNeedingSummary(batchSize);

  if (pages.length === 0) {
    console.log('[notion] No pages need AI summarization');
    return;
  }

  let summarized = 0;
  let failed = 0;

  for (const page of pages) {
    try {
      const trimmed = page.content_text.trim();
      const hasContent = trimmed.length >= 50;

      // Classify: category, sentiment, entities, topics — all in one LLM call
      const classifyInput = hasContent
        ? `Title: ${page.title}\nContent: ${trimmed.substring(0, 1000)}`
        : `Title: ${page.title}`;
      const classification = inferClassification(classifyInput);

      let summary: string;

      if (!hasContent) {
        // No meaningful content: use title as summary
        summary = page.title;
      } else {
        // Build prompt with metadata context
        const metaParts: string[] = [`Title: ${page.title}`];
        if (page.url) metaParts.push(`URL: ${page.url}`);
        metaParts.push(`Created: ${page.created_time}`);
        metaParts.push(`Last edited: ${page.last_edited_time}`);
        const metaBlock = metaParts.join('\n');

        // Try with progressively smaller content if model context overflows
        const result = summarizeWithFallback(trimmed, metaBlock);
        if (!result) continue;
        summary = result;
      }

      // Merge structured entities (from Notion properties) with LLM-inferred entities
      const structuredEnts = getPageStructuredEntities?.(page.id) ?? [];
      const mergedEntities = mergeEntities(structuredEnts, classification.entities);

      // Store in summaries table (synced=0, will be sent to server later)
      insertSummaryFn({
        pageId: page.id,
        summary,
        category: classification.category,
        sentiment: classification.sentiment,
        entities: mergedEntities.map(e => ({
          id: e.id,
          dataSourceId: 'notionId',
          type: e.type === 'page' ? 'other' : e.type,
          name: e.name,
          role: e.role,
        })),
        topics: classification.topics,
        metadata: {
          pageId: page.id,
          pageTitle: page.title,
          pageUrl: page.url,
          lastEditedTime: page.last_edited_time,
          createdTime: page.created_time,
          contentLength: trimmed.length,
          noContent: !hasContent,
        },
        sourceCreatedAt: new Date(page.created_time).toISOString(),
        sourceUpdatedAt: new Date(page.last_edited_time).toISOString(),
      });

      summarized++;
    } catch (e) {
      console.error(`[notion] Failed to summarize page ${page.id} ("${page.title}"): ${e}`);
      failed++;
    }
  }

  console.log(
    `[notion] AI summaries: ${summarized} pages summarized${failed > 0 ? `, ${failed} failed` : ''}`
  );
}

/**
 * Phase 4b: Sync unsynced summaries to the server.
 * Reads summaries with synced=0, submits each via model.submitSummary(),
 * and marks them as synced on success.
 */
function syncSummariesToServer(): void {
  const getUnsyncedSummariesFn = (globalThis as Record<string, unknown>).getUnsyncedSummaries as
    | ((limit: number) => Array<{
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
      }>)
    | undefined;
  const markSummariesSyncedFn = (globalThis as Record<string, unknown>).markSummariesSynced as
    | ((ids: number[]) => void)
    | undefined;

  if (!getUnsyncedSummariesFn || !markSummariesSyncedFn) return;

  const batch = getUnsyncedSummariesFn(100);
  if (batch.length === 0) {
    console.log('[notion] No unsynced summaries to send');
    return;
  }

  let sent = 0;
  let failed = 0;
  const syncedIds: number[] = [];

  for (const row of batch) {
    try {
      // Parse stored JSON fields
      const entities: SummaryEntity[] = row.entities ? JSON.parse(row.entities) : [];
      const topics: string[] = row.topics ? JSON.parse(row.topics) : [];
      const metadata: Record<string, unknown> = row.metadata ? JSON.parse(row.metadata) : {};

      model.submitSummary({
        summary: row.summary,
        category: row.category || undefined,
        dataSource: 'notion',
        sentiment: (row.sentiment as 'positive' | 'neutral' | 'negative' | 'mixed') || 'neutral',
        keyPoints: topics.length > 0 ? topics : undefined,
        entities: entities.length > 0 ? entities : undefined,
        metadata,
        createdAt: row.source_created_at,
        updatedAt: row.source_updated_at,
      });

      syncedIds.push(row.id);
      sent++;
    } catch (e) {
      console.error(`[notion] Failed to sync summary ${row.id} (page ${row.page_id}): ${e}`);
      failed++;
    }
  }

  // Mark successfully sent summaries as synced
  if (syncedIds.length > 0) {
    markSummariesSyncedFn(syncedIds);
  }

  console.log(
    `[notion] Server sync: ${sent} summaries sent${failed > 0 ? `, ${failed} failed` : ''}`
  );
}

// ---------------------------------------------------------------------------
// State publishing helper
// ---------------------------------------------------------------------------

function publishSyncState(): void {
  const s = globalThis.getNotionSkillState();

  state.setPartial({
    connected: !!oauth.getCredential(),
    workspaceName: s.config.workspaceName || null,
    syncInProgress: s.syncStatus.syncInProgress,
    lastSyncTime: s.syncStatus.lastSyncTime
      ? new Date(s.syncStatus.lastSyncTime).toISOString()
      : null,
    nextSyncTime: s.syncStatus.nextSyncTime
      ? new Date(s.syncStatus.nextSyncTime).toISOString()
      : null,
    totalPages: s.syncStatus.totalPages,
    totalDatabases: s.syncStatus.totalDatabases,
    totalUsers: s.syncStatus.totalUsers,
    pagesWithContent: s.syncStatus.pagesWithContent,
    pagesWithSummary: s.syncStatus.pagesWithSummary,
    summariesTotal: s.syncStatus.summariesTotal,
    summariesPending: s.syncStatus.summariesPending,
    lastSyncError: s.syncStatus.lastSyncError,
    lastSyncDurationMs: s.syncStatus.lastSyncDurationMs,
  });
}

// Expose on globalThis
const _g = globalThis as Record<string, unknown>;
_g.performSync = performSync;
_g.publishSyncState = publishSyncState;
_g.inferClassification = inferClassification;
_g.mergeEntities = mergeEntities;
_g.summarizeWithFallback = summarizeWithFallback;
_g.generateSummaries = generateSummaries;
_g.syncSummariesToServer = syncSummariesToServer;
