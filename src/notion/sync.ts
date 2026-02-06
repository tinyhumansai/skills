// Notion sync engine
// Periodically downloads pages, databases, users, and page content from Notion
// into local SQLite for fast local querying.
import './skill-state';
import type { NotionGlobals } from './types';

// Access helpers at runtime via the same n() pattern used by tools
const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
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

    // Update sync state
    const durationMs = Date.now() - startTime;
    s.syncStatus.lastSyncTime = Date.now();
    s.syncStatus.nextSyncTime = Date.now() + s.config.syncIntervalMinutes * 60 * 1000;
    s.syncStatus.lastSyncDurationMs = durationMs;

    // Persist sync time in database
    const { setNotionSyncState, getEntityCounts } = n();
    setNotionSyncState('last_sync_time', s.syncStatus.lastSyncTime.toString());

    // Update counts
    const counts = getEntityCounts();
    s.syncStatus.totalPages = counts.pages;
    s.syncStatus.totalDatabases = counts.databases;
    s.syncStatus.totalUsers = counts.users;
    s.syncStatus.pagesWithContent = counts.pagesWithContent;

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
  const { notionFetch } = n();
  const upsertUser = (globalThis as Record<string, unknown>).upsertUser as
    | ((user: Record<string, unknown>) => void)
    | undefined;
  if (!upsertUser) return;

  let startCursor: string | undefined;
  let hasMore = true;
  let count = 0;

  while (hasMore) {
    const endpoint = `/users?page_size=100${startCursor ? `&start_cursor=${startCursor}` : ''}`;
    const result = notionFetch(endpoint) as {
      results: Record<string, unknown>[];
      has_more: boolean;
      next_cursor?: string;
    };

    for (const user of result.results) {
      upsertUser(user);
      count++;
    }

    hasMore = result.has_more;
    startCursor = result.next_cursor as string | undefined;
  }

  console.log(`[notion] Synced ${count} users`);
}

// ---------------------------------------------------------------------------
// Phase 2: Sync pages and databases via search (incremental)
// ---------------------------------------------------------------------------

function syncSearchItems(): void {
  const { notionFetch, getNotionSyncState, setNotionSyncState } = n();
  const upsertPage = (globalThis as Record<string, unknown>).upsertPage as
    | ((page: Record<string, unknown>) => void)
    | undefined;
  const upsertDatabase = (globalThis as Record<string, unknown>).upsertDatabase as
    | ((database: Record<string, unknown>) => void)
    | undefined;

  if (!upsertPage || !upsertDatabase) return;

  const lastSyncTimeStr = getNotionSyncState('last_sync_time');
  const lastSyncTime = lastSyncTimeStr ? parseInt(lastSyncTimeStr, 10) : 0;
  const isFirstSync = lastSyncTime === 0;

  let startCursor: string | undefined;
  let hasMore = true;
  let pageCount = 0;
  let dbCount = 0;
  let totalFetched = 0;
  const maxFirstSync = 500;
  let reachedOldItems = false;

  while (hasMore && !reachedOldItems) {
    const body: Record<string, unknown> = {
      page_size: 100,
      sort: { direction: 'descending', timestamp: 'last_edited_time' },
    };
    if (startCursor) body.start_cursor = startCursor;

    const result = notionFetch('/search', { method: 'POST', body }) as {
      results: Record<string, unknown>[];
      has_more: boolean;
      next_cursor?: string;
    };

    for (const item of result.results) {
      const lastEdited = item.last_edited_time as string;
      const editedMs = new Date(lastEdited).getTime();

      // Incremental: stop when we reach items older than last sync
      if (!isFirstSync && editedMs <= lastSyncTime) {
        reachedOldItems = true;
        break;
      }

      if (item.object === 'page') {
        upsertPage(item);
        pageCount++;
      } else if (item.object === 'database') {
        upsertDatabase(item);
        dbCount++;
      }

      totalFetched++;
    }

    // For first sync, cap at maxFirstSync to avoid blocking
    if (isFirstSync && totalFetched >= maxFirstSync) {
      console.log(`[notion] First sync capped at ${maxFirstSync} items`);
      break;
    }

    hasMore = result.has_more;
    startCursor = result.next_cursor as string | undefined;
  }

  // Record that sync happened (even if first sync was partial)
  setNotionSyncState('last_search_sync', Date.now().toString());

  console.log(`[notion] Synced ${pageCount} pages, ${dbCount} databases`);
}

// ---------------------------------------------------------------------------
// Phase 3: Sync page content (block text extraction)
// ---------------------------------------------------------------------------

function syncContent(): void {
  const s = globalThis.getNotionSkillState();
  const { fetchBlockTreeText } = n();
  const getPagesNeedingContent = (globalThis as Record<string, unknown>).getPagesNeedingContent as
    | ((limit: number) => Array<{ id: string; title: string }>)
    | undefined;
  const updatePageContent = (globalThis as Record<string, unknown>).updatePageContent as
    | ((pageId: string, text: string) => void)
    | undefined;

  if (!getPagesNeedingContent || !updatePageContent) return;

  const batchSize = s.config.maxPagesPerContentSync;
  const pages = getPagesNeedingContent(batchSize);
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
    lastSyncError: s.syncStatus.lastSyncError,
    lastSyncDurationMs: s.syncStatus.lastSyncDurationMs,
  });
}

// Expose on globalThis
const _g = globalThis as Record<string, unknown>;
_g.performSync = performSync;
_g.publishSyncState = publishSyncState;
