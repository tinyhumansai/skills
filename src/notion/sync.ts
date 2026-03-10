// Notion sync engine
// Periodically downloads pages, databases, users, and page content from Notion
// into local SQLite for fast local querying.
import { notionApi } from './api/index';
import type { LocalDatabaseRow, LocalPage } from './db/helpers';
import {
  getDatabaseById,
  getDatabaseRowById,
  getEntityCounts,
  getLocalDatabases,
  getPageById,
  getPagesNeedingContent,
  getUnsubmittedPages,
  getUnsubmittedRows,
  getUnsyncedSummaries,
  markPagesSubmitted,
  markRowsSubmitted,
  markSummariesSynced,
  updatePageContent,
  upsertDatabase,
  upsertDatabaseRow,
  upsertPage,
  upsertUser,
} from './db/helpers';
import { fetchBlockTreeText } from './helpers';
import { getNotionSkillState } from './state';

// ---------------------------------------------------------------------------
// Main sync orchestrator
// ---------------------------------------------------------------------------

export function performSync(): void {
  const s = getNotionSkillState();

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

  (async () => {
    try {
      // Phase 1: Sync users
      console.log('[notion] Sync phase 1: users');
      await syncUsers();

      // Phase 2: Sync pages and databases via search
      console.log('[notion] Sync phase 2: pages & databases');
      await syncSearchItems();

      // Phase 2.5: Sync database rows (time-budgeted to avoid Rust async timeout)
      console.log('[notion] Sync phase 2.5: database rows');
      await syncDatabaseRows(startTime, CONTENT_SYNC_TIME_BUDGET_MS);

      // Phase 3: Sync page content (block text, time-budgeted to avoid Rust async timeout)
      if (s.config.contentSyncEnabled) {
        console.log('[notion] Sync phase 3: page content');
        await syncContent(startTime, CONTENT_SYNC_TIME_BUDGET_MS);
      }

      // Phase 4: Sync unsynced summaries to the server
      console.log('[notion] Sync phase 4: sync summaries to server');
      // syncSummariesToServer();

      // Phase 5: Submit new data to backend for processing
      console.log('[notion] Sync phase 5: submit new data to backend');
      await submitNewData();

      // Update sync state
      const durationMs = Date.now() - startTime;
      const nowMs = Date.now();
      s.syncStatus.nextSyncTime = nowMs + s.config.syncIntervalMinutes * 60 * 1000;
      s.syncStatus.lastSyncDurationMs = durationMs;

      // Only advance lastSyncTime if we actually have items in the DB.
      // This prevents the incremental sync from skipping everything on the
      // next run if the first sync stored 0 items (e.g. due to errors).
      const counts = getEntityCounts();
      if (counts.pages > 0 || counts.databases > 0) {
        s.syncStatus.lastSyncTime = nowMs;
      }

      // Update counts
      s.syncStatus.totalPages = counts.pages;
      s.syncStatus.totalDatabases = counts.databases;
      s.syncStatus.pagesWithContent = counts.pagesWithContent;
      s.syncStatus.pagesWithSummary = counts.pagesWithSummary;
      s.syncStatus.summariesTotal = counts.summariesTotal;
      s.syncStatus.summariesPending = counts.summariesPending;

      s.syncStatus.totalDatabaseRows = counts.databaseRows;

      console.log(
        `[notion] Sync complete in ${durationMs}ms — ${counts.pages} pages, ${counts.databases} databases, ${counts.databaseRows} db rows`
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
  })();
}

// ---------------------------------------------------------------------------
// Phase 1: Sync users
// ---------------------------------------------------------------------------

async function syncUsers(): Promise<void> {
  let startCursor: string | undefined;
  let hasMore = true;
  let count = 0;

  while (hasMore) {
    const result = await notionApi.listUsers(100, startCursor);

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

async function syncSearchItems(): Promise<void> {
  const s = getNotionSkillState();
  const lastSyncTime = s.syncStatus.lastSyncTime;
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

    const result = await notionApi.search(body);

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
  const dsResult = await syncDataSources(
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
  state.set('last_search_sync', Date.now());

  const skipMsg =
    pageSkipped > 0 || dbSkipped > 0 ? ` (${pageSkipped} pages, ${dbSkipped} dbs unchanged)` : '';
  const errorMsg = errorCount > 0 ? `, ${errorCount} errors` : '';
  console.log(
    `[notion] Synced ${pageCount} pages, ${dbCount} databases (last 30 days)${skipMsg}${errorMsg}`
  );
}

async function syncDataSources(
  upsertDatabase: (db: Record<string, unknown>) => void,
  getDatabaseById: ((id: string) => { last_edited_time: string } | null) | undefined,
  cutoffMs: number,
  lastSyncTime: number,
  isFirstSync: boolean
): Promise<{ count: number; skipped: number; errors: number }> {
  let startCursor: string | undefined;
  let hasMore = true;
  let count = 0;
  let skipped = 0;
  let errors = 0;
  let reachedOldItems = false;

  while (hasMore && !reachedOldItems) {
    const result = await notionApi.search({
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
// Phase 2.5: Sync database rows
// For each synced database, query its rows and store them locally.
// ---------------------------------------------------------------------------

/** Max rows to sync per database per sync cycle */
const MAX_ROWS_PER_DATABASE = 200;

/**
 * Maximum ms for phases 3+ (content sync, submit) to prevent the Rust async
 * operation timeout (~120s). Mirrors the google-drive sync time budget pattern.
 * Budget is measured from the overall sync startTime.
 */
const CONTENT_SYNC_TIME_BUDGET_MS = 18_000;

async function syncDatabaseRows(startTime: number, budgetMs: number): Promise<void> {
  // Get all locally synced databases
  const databases = getLocalDatabases({ limit: 100 }) as Array<{ id: string; title: string }>;

  if (databases.length === 0) {
    console.log('[notion] No databases to sync rows for');
    return;
  }

  const s = getNotionSkillState();
  const lastSyncTime = s.syncStatus.lastSyncTime;
  const isFirstSync = lastSyncTime === 0;

  let totalRowCount = 0;
  let totalSkipped = 0;
  let totalErrors = 0;
  let dbsSynced = 0;

  for (const database of databases) {
    if (Date.now() - startTime > budgetMs) {
      console.log('[notion] DB row sync time budget reached, deferring remaining databases');
      break;
    }
    try {
      let startCursor: string | undefined;
      let hasMore = true;
      let rowCount = 0;
      let skipped = 0;
      let fetched = 0;
      let reachedOldRows = false;

      while (hasMore && fetched < MAX_ROWS_PER_DATABASE && !reachedOldRows) {
        const body: Record<string, unknown> = {
          page_size: 100,
          sorts: [{ timestamp: 'last_edited_time', direction: 'descending' }],
        };
        if (startCursor) body.start_cursor = startCursor;

        let result: { results: Record<string, unknown>[]; has_more: boolean; next_cursor?: string };
        try {
          result = (await notionApi.queryDataSource(database.id, body)) as typeof result;
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          // Skip databases we can't query (permissions, deleted, etc.)
          if (
            msg.includes('404') ||
            msg.includes('403') ||
            msg.includes('no data sources') ||
            msg.includes('Could not find')
          ) {
            console.warn(
              `[notion] Cannot query database "${database.title}" (${database.id}): ${msg}`
            );
            break;
          }
          throw e;
        }

        for (const row of result.results) {
          const rec = row as Record<string, unknown>;
          const lastEdited = rec.last_edited_time as string;

          // Incremental: stop when we reach rows older than last sync
          if (!isFirstSync && lastEdited) {
            const editedMs = new Date(lastEdited).getTime();
            if (editedMs <= lastSyncTime) {
              reachedOldRows = true;
              break;
            }
          }

          // Skip if unchanged
          const existing = getDatabaseRowById?.(rec.id as string);
          if (existing && existing.last_edited_time === lastEdited) {
            skipped++;
            fetched++;
            continue;
          }

          try {
            upsertDatabaseRow(rec, database.id);
            rowCount++;
          } catch (e) {
            console.error(
              `[notion] Failed to upsert row ${rec.id} in database ${database.id}: ${e}`
            );
            totalErrors++;
          }
          fetched++;
        }

        hasMore = result.has_more;
        startCursor = result.next_cursor as string | undefined;
      }

      totalRowCount += rowCount;
      totalSkipped += skipped;
      if (rowCount > 0 || skipped > 0) dbsSynced++;

      if (rowCount > 0) {
        console.log(
          `[notion] Database "${database.title}": ${rowCount} rows synced${skipped > 0 ? `, ${skipped} unchanged` : ''}`
        );
      }
    } catch (e) {
      console.error(
        `[notion] Failed to sync rows for database "${database.title}" (${database.id}): ${e}`
      );
      totalErrors++;
    }
  }

  const skipMsg = totalSkipped > 0 ? ` (${totalSkipped} unchanged)` : '';
  const errorMsg = totalErrors > 0 ? `, ${totalErrors} errors` : '';
  console.log(
    `[notion] Database row sync: ${totalRowCount} rows across ${dbsSynced} databases${skipMsg}${errorMsg}`
  );
}

// ---------------------------------------------------------------------------
// Phase 3: Sync page content (block text extraction)
// ---------------------------------------------------------------------------

async function syncContent(startTime: number, budgetMs: number): Promise<void> {
  const s = getNotionSkillState();
  const batchSize = s.config.maxPagesPerContentSync;
  const cutoffIso = new Date(Date.now() - THIRTY_DAYS_MS).toISOString();
  const pages = getPagesNeedingContent(batchSize, cutoffIso);
  let synced = 0;
  let failed = 0;

  for (const page of pages) {
    if (Date.now() - startTime > budgetMs) {
      console.log('[notion] Content sync time budget reached, deferring remaining pages');
      break;
    }
    try {
      const text = await fetchBlockTreeText(page.id, 2);
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
// Phase 4: Sync unsynced summaries to the server
// ---------------------------------------------------------------------------

/**
 * Sync unsynced summaries to the server via net.fetch().
 * Reads summaries with synced=0, submits each to the backend API,
 * and marks them as synced on success.
 * Reserved for Phase 4 — currently not called to avoid extra network dependency.
 */
async function _syncSummariesToServer(): Promise<void> {
  const batch = getUnsyncedSummaries(100);
  if (batch.length === 0) {
    console.log('[notion] No unsynced summaries to send');
    return;
  }

  // Get backend URL and auth token from environment
  const backendUrl = platform.env('BACKEND_URL');
  const authToken = platform.env('AUTH_TOKEN');

  if (!backendUrl || !authToken) {
    console.warn('[notion] Missing BACKEND_URL or AUTH_TOKEN — skipping summary sync');
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

      const submission: SummarySubmission = {
        summary: row.summary,
        url: row.url || undefined,
        category: row.category || undefined,
        dataSource: 'notion',
        sentiment: (row.sentiment as 'positive' | 'neutral' | 'negative' | 'mixed') || 'neutral',
        keyPoints: topics.length > 0 ? topics : undefined,
        entities: entities.length > 0 ? entities : undefined,
        metadata,
        createdAt: row.source_created_at,
        updatedAt: row.source_updated_at,
      };

      const resp = await net.fetch(`${backendUrl}/api/summaries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
        body: JSON.stringify(submission),
        timeout: 10000,
      });

      if (resp.status >= 400) {
        console.error(`[notion] Summary submit failed (${resp.status}): ${resp.body}`);
        failed++;
        continue;
      }

      syncedIds.push(row.id);
      sent++;
    } catch (e) {
      console.error(`[notion] Failed to sync summary ${row.id} (page ${row.page_id}): ${e}`);
      failed++;
    }
  }

  // Mark successfully sent summaries as synced
  if (syncedIds.length > 0) {
    markSummariesSynced(syncedIds);
  }

  console.log(
    `[notion] Server sync: ${sent} summaries sent${failed > 0 ? `, ${failed} failed` : ''}`
  );
}
void _syncSummariesToServer; // Reserved for Phase 4; reference to avoid TS6133

// ---------------------------------------------------------------------------
// Phase 5: Submit new data to backend for processing
// ---------------------------------------------------------------------------

/** Approximate max payload size per socket message (~100 KB). */
const MAX_BATCH_BYTES = 100 * 1024;

/** Max items to pull from DB per submission round. */
const SUBMIT_QUERY_LIMIT = 500;

/**
 * Parse page_entities JSON into DataSubmissionEntity array.
 * Resolves user names from the users table.
 */
function parsePageEntities(
  page: LocalPage
): Array<{ name: string; identifier: string; kind: string }> | undefined {
  if (!page.page_entities) return undefined;

  let raw: Array<{ id: string; type: string; name?: string; role: string }>;
  try {
    raw = JSON.parse(page.page_entities);
  } catch {
    return undefined;
  }
  if (!Array.isArray(raw) || raw.length === 0) return undefined;

  const cid = getNotionSkillState().config.credentialId;
  const entities: Array<{ name: string; identifier: string; kind: string }> = [];
  const seen = new Set<string>();

  for (const e of raw) {
    if (seen.has(e.id)) continue;
    seen.add(e.id);

    let name = e.name;
    if (!name && e.type === 'person') {
      const user = db.get('SELECT name FROM users WHERE credential_id = ? AND id = ?', [
        cid,
        e.id,
      ]) as { name: string } | null;
      if (user) name = user.name;
    }
    entities.push({ name: name || e.id, identifier: e.id, kind: e.type || 'person' });
  }

  return entities.length > 0 ? entities : undefined;
}

/**
 * Build a DataSubmissionChunk from a page row.
 * Uses content_text for the body content (extracted from page blocks).
 */
function pageToChunk(page: LocalPage): DataSubmissionChunk {
  const content = page.content_text || '';
  return {
    title: page.title || undefined,
    content,
    entities: parsePageEntities(page),
    metadata: {
      pageId: page.id,
      url: page.url,
      parentType: page.parent_type,
      parentId: page.parent_id,
      createdTime: page.created_time,
      lastEditedTime: page.last_edited_time,
    },
  };
}

/**
 * Build a DataSubmissionChunk from a database row.
 * Uses properties_text for the body content (flattened property values).
 * Sends properties_json as rawContent for downstream raw processing.
 */
function rowToChunk(row: LocalDatabaseRow): DataSubmissionChunk {
  const content = row.properties_text || '';
  return {
    title: row.title || undefined,
    content,
    rawContent: row.properties_json || undefined,
    metadata: {
      rowId: row.id,
      databaseId: row.database_id,
      url: row.url,
      createdTime: row.created_time,
      lastEditedTime: row.last_edited_time,
    },
  };
}

/** Rough byte size of a chunk (title + content + rawContent + overhead). */
function estimateChunkSize(chunk: DataSubmissionChunk): number {
  return (chunk.title?.length || 0) + chunk.content.length + (chunk.rawContent?.length || 0) + 256;
}

/**
 * Submit un-submitted pages and database rows to the backend for processing.
 * Batches chunks so each socket message stays under ~100 KB.
 * Marks items as submitted only after backend.submitData resolves successfully.
 */
async function submitNewData(): Promise<void> {
  const pages = getUnsubmittedPages(SUBMIT_QUERY_LIMIT);
  const rows = getUnsubmittedRows(SUBMIT_QUERY_LIMIT);

  if (pages.length === 0 && rows.length === 0) return;

  // Build chunks from both pages and rows
  const prepared: Array<{
    id: string;
    type: 'page' | 'row';
    chunk: ReturnType<typeof pageToChunk>;
  }> = [];
  const emptyPageIds: string[] = [];
  const emptyRowIds: string[] = [];

  for (const page of pages) {
    const chunk = pageToChunk(page);
    if (chunk.content.length > 0) {
      prepared.push({ id: page.id, type: 'page', chunk });
    } else {
      emptyPageIds.push(page.id);
    }
  }

  for (const row of rows) {
    const chunk = rowToChunk(row);
    if (chunk.content.length > 0) {
      prepared.push({ id: row.id, type: 'row', chunk });
    } else {
      emptyRowIds.push(row.id);
    }
  }

  // Mark empty-content items as submitted so they aren't re-processed
  if (emptyPageIds.length > 0) markPagesSubmitted(emptyPageIds);
  if (emptyRowIds.length > 0) markRowsSubmitted(emptyRowIds);
  if (prepared.length === 0) return;

  // Split into size-limited batches
  let batch: Array<ReturnType<typeof pageToChunk>> = [];
  let batchPageIds: string[] = [];
  let batchRowIds: string[] = [];
  let batchBytes = 0;
  let totalSubmitted = 0;

  const flushBatch = async (): Promise<boolean> => {
    if (batch.length === 0) return true;
    const pageIds = batchPageIds.slice();
    const rowIds = batchRowIds.slice();
    const batchLength = batch.length;
    try {
      await backend.submitData(batch, { dataSource: 'notion' });
      if (pageIds.length > 0) markPagesSubmitted(pageIds);
      if (rowIds.length > 0) markRowsSubmitted(rowIds);
      totalSubmitted += batchLength;
      return true;
    } catch (error) {
      console.error(`[notion] Failed to submit batch to backend: ${error}`);
      return false;
    } finally {
      batch = [];
      batchPageIds = [];
      batchRowIds = [];
      batchBytes = 0;
    }
  };

  for (const { id, type, chunk } of prepared) {
    const size = estimateChunkSize(chunk);

    // If adding this chunk would exceed the limit, flush the current batch first (unless batch is empty — allow single oversized chunk)
    if (batch.length > 0 && batchBytes + size > MAX_BATCH_BYTES) {
      if (!(await flushBatch())) return; // Stop on failure; remaining items retried next sync
    }

    batch.push(chunk);
    if (type === 'page') batchPageIds.push(id);
    else batchRowIds.push(id);
    batchBytes += size;

    // When batch was empty and this single chunk is oversized, send it immediately as an oversized payload
    if (batch.length === 1 && batchBytes > MAX_BATCH_BYTES) {
      if (!(await flushBatch())) return;
    }
  }

  // Flush remaining batch
  await flushBatch();

  if (totalSubmitted > 0) {
    console.log(`[notion] Submitted ${totalSubmitted} item(s) to backend`);
  }
}

// ---------------------------------------------------------------------------
// State publishing helper
// ---------------------------------------------------------------------------

function publishSyncState(): void {
  const s = getNotionSkillState();
  const isConnected = !!oauth.getCredential();

  state.setPartial({
    // Standard SkillHostConnectionState fields
    connection_status: isConnected ? 'connected' : 'disconnected',
    auth_status: isConnected ? 'authenticated' : 'not_authenticated',
    connection_error: s.syncStatus.lastSyncError || null,
    auth_error: null,
    is_initialized: isConnected,
    // Skill-specific fields
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
    totalDatabaseRows: s.syncStatus.totalDatabaseRows,
    pagesWithContent: s.syncStatus.pagesWithContent,
    pagesWithSummary: s.syncStatus.pagesWithSummary,
    summariesTotal: s.syncStatus.summariesTotal,
    summariesPending: s.syncStatus.summariesPending,
    lastSyncError: s.syncStatus.lastSyncError,
    lastSyncDurationMs: s.syncStatus.lastSyncDurationMs,
  });
}
