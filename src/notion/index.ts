// notion/index.ts
// Notion integration skill exposing 25 tools for the Notion API + local sync.
// Supports pages, databases, blocks, users, comments, and local search.
// Authentication is handled via the platform OAuth bridge.
// Import modules to initialize state and expose functions on globalThis
// Side-effect import: triggers api module initialization.
// Do NOT destructure — `import { notionApi }` is broken by IIFE CJS interop.
// The api/index.ts module writes notionApi to globalThis.exports at init time.
import './api/index';
import './db-helpers';
import './db-schema';
// Import helpers
import {
  buildParagraphBlock,
  buildRichText,
  fetchBlockTreeText,
  formatApiError,
  formatBlockContent,
  formatBlockSummary,
  formatDatabaseSummary,
  formatPageSummary,
  formatPageTitle,
  formatRichText,
  formatUserSummary,
  notionFetch,
} from './helpers';
import './skill-state';
import type { NotionSkillConfig } from './skill-state';
import './sync';
import { appendBlocksTool } from './tools/append-blocks';
import { appendTextTool } from './tools/append-text';
import { createCommentTool } from './tools/create-comment';
import { createDatabaseTool } from './tools/create-database';
import { createPageTool } from './tools/create-page';
import { deleteBlockTool } from './tools/delete-block';
import { deletePageTool } from './tools/delete-page';
import { getBlockTool } from './tools/get-block';
import { getBlockChildrenTool } from './tools/get-block-children';
import { getDatabaseTool } from './tools/get-database';
import { getPageTool } from './tools/get-page';
import { getPageContentTool } from './tools/get-page-content';
import { getUserTool } from './tools/get-user';
import { listAllDatabasesTool } from './tools/list-all-databases';
import { listAllPagesTool } from './tools/list-all-pages';
import { listCommentsTool } from './tools/list-comments';
import { listUsersTool } from './tools/list-users';
import { queryDatabaseTool } from './tools/query-database';
// Import tools
import { searchTool } from './tools/search';
import { searchLocalTool } from './tools/search-local';
import { summarizePagesTool } from './tools/summarize-pages';
import { syncNowTool } from './tools/sync-now';
import { syncStatusTool } from './tools/sync-status';
import { updateBlockTool } from './tools/update-block';
import { updateDatabaseTool } from './tools/update-database';
import { updatePageTool } from './tools/update-page';

// ---------------------------------------------------------------------------
// Expose helpers on globalThis for tools to access at runtime
// ---------------------------------------------------------------------------

const _g = globalThis as Record<string, unknown>;
// notionApi was built by api/index.ts and written to globalThis.exports.notionApi.
// Read it from there (module import would be empty due to IIFE CJS interop).
_g.notionApi = (
  (globalThis as unknown as Record<string, unknown>).exports as Record<string, unknown>
)?.notionApi;
_g.notionFetch = notionFetch;
_g.formatApiError = formatApiError;
_g.formatRichText = formatRichText;
_g.formatPageTitle = formatPageTitle;
_g.formatPageSummary = formatPageSummary;
_g.formatDatabaseSummary = formatDatabaseSummary;
_g.formatBlockContent = formatBlockContent;
_g.formatBlockSummary = formatBlockSummary;
_g.formatUserSummary = formatUserSummary;
_g.buildRichText = buildRichText;
_g.buildParagraphBlock = buildParagraphBlock;
_g.fetchBlockTreeText = fetchBlockTreeText;

// ---------------------------------------------------------------------------
// Lifecycle hooks
// ---------------------------------------------------------------------------

function init(): void {
  console.log('[notion] Initializing');
  const s = globalThis.getNotionSkillState();

  // Initialize database schema
  const initSchema = (globalThis as { initializeNotionSchema?: () => void }).initializeNotionSchema;
  if (initSchema) initSchema();

  // Load persisted config from store
  const saved = state.get('config') as Partial<NotionSkillConfig> | null;
  if (saved) {
    s.config.credentialId = saved.credentialId || s.config.credentialId;
    s.config.workspaceName = saved.workspaceName || s.config.workspaceName;
    s.config.syncIntervalMinutes = saved.syncIntervalMinutes || s.config.syncIntervalMinutes;
    s.config.contentSyncEnabled = saved.contentSyncEnabled ?? s.config.contentSyncEnabled;
    s.config.maxPagesPerContentSync =
      saved.maxPagesPerContentSync || s.config.maxPagesPerContentSync;
  }

  // Load sync state from store
  const lastSync = state.get('last_sync_time') as number | null;
  if (lastSync) s.syncStatus.lastSyncTime = lastSync;

  // Load entity counts
  const getEntityCounts = (
    globalThis as {
      getEntityCounts?: () => {
        pages: number;
        databases: number;
        users: number;
        pagesWithContent: number;
        pagesWithSummary: number;
      };
    }
  ).getEntityCounts;
  if (getEntityCounts) {
    const counts = getEntityCounts();
    s.syncStatus.totalPages = counts.pages;
    s.syncStatus.totalDatabases = counts.databases;
    s.syncStatus.totalUsers = counts.users;
    s.syncStatus.pagesWithContent = counts.pagesWithContent;
    s.syncStatus.pagesWithSummary = counts.pagesWithSummary;
  }

  const cred = oauth.getCredential();
  if (cred) {
    s.config.credentialId = cred.credentialId;
    console.log(`[notion] Connected to workspace: ${s.config.workspaceName || '(unnamed)'}`);
  } else {
    console.log('[notion] No OAuth credential — waiting for setup');
  }

  publishState();
}

function start(): void {
  const s = globalThis.getNotionSkillState();

  if (!oauth.getCredential()) {
    console.log('[notion] No credential — skill inactive until OAuth completes');
    return;
  }

  // Register sync cron schedule
  const cronExpr = `0 */${s.config.syncIntervalMinutes} * * * *`;
  cron.register('notion-sync', cronExpr);
  console.log(`[notion] Scheduled sync every ${s.config.syncIntervalMinutes} minutes`);

  // Perform initial sync (skip if sync was attempted in the last 10 mins)
  const TEN_MINS_MS = 10 * 60 * 1000;
  const lastSync = s.syncStatus.lastSyncTime;
  const recentlySynced = lastSync > 0 && Date.now() - lastSync < TEN_MINS_MS;
  const doSync = (globalThis as { performSync?: () => void }).performSync;
  if (doSync && !recentlySynced) {
    doSync();
  } else if (recentlySynced) {
    console.log('[notion] Skipping initial sync — last sync was within 10 minutes');
  }

  console.log('[notion] Started');
  publishState();
}

function stop(): void {
  console.log('[notion] Stopping');
  const s = globalThis.getNotionSkillState();

  // Unregister cron
  cron.unregister('notion-sync');

  // Persist config
  state.set('config', s.config);

  // Persist sync state
  state.set('last_sync_time', s.syncStatus.lastSyncTime);

  state.set('status', 'stopped');
  console.log('[notion] Stopped');
}

function onCronTrigger(scheduleId: string): void {
  console.log(`[notion] Cron triggered: ${scheduleId}`);

  if (scheduleId === 'notion-sync') {
    const doSync = (globalThis as { performSync?: () => void }).performSync;
    if (doSync) {
      doSync();
    }
  }
}

// ---------------------------------------------------------------------------
// Session lifecycle
// ---------------------------------------------------------------------------

function onSessionStart(args: { sessionId: string }): void {
  const s = globalThis.getNotionSkillState();
  s.activeSessions.push(args.sessionId);
}

function onSessionEnd(args: { sessionId: string }): void {
  const s = globalThis.getNotionSkillState();
  const index = s.activeSessions.indexOf(args.sessionId);
  if (index > -1) {
    s.activeSessions.splice(index, 1);
  }
}

// ---------------------------------------------------------------------------
// OAuth lifecycle
// ---------------------------------------------------------------------------

function onOAuthComplete(args: OAuthCompleteArgs): OAuthCompleteResult | void {
  const s = globalThis.getNotionSkillState();
  s.config.credentialId = args.credentialId;
  console.log(
    `[notion] OAuth complete — credential: ${args.credentialId}, account: ${args.accountLabel || '(unknown)'}`
  );

  if (args.accountLabel) {
    s.config.workspaceName = args.accountLabel;
  }

  state.set('config', s.config);

  // Start sync schedule and trigger initial sync
  const cronExpr = `0 */${s.config.syncIntervalMinutes} * * * *`;
  cron.register('notion-sync', cronExpr);

  const doSync = (globalThis as { performSync?: () => void }).performSync;
  if (doSync) {
    doSync();
  }

  publishState();
}

function onOAuthRevoked(args: OAuthRevokedArgs): void {
  console.log(`[notion] OAuth revoked — reason: ${args.reason}`);
  const s = globalThis.getNotionSkillState();

  s.config.credentialId = '';
  s.config.workspaceName = '';
  state.delete('config');
  cron.unregister('notion-sync');
  publishState();
}

function onDisconnect(): void {
  console.log('[notion] Disconnecting');
  const s = globalThis.getNotionSkillState();

  oauth.revoke();
  s.config.credentialId = '';
  s.config.workspaceName = '';
  state.delete('config');
  cron.unregister('notion-sync');
  publishState();
}

// ---------------------------------------------------------------------------
// Options system
// ---------------------------------------------------------------------------

function onListOptions(): { options: SkillOption[] } {
  const s = globalThis.getNotionSkillState();

  return {
    options: [
      {
        name: 'syncInterval',
        type: 'select',
        label: 'Sync Interval',
        value: s.config.syncIntervalMinutes.toString(),
        options: [
          { label: 'Every 10 minutes', value: '10' },
          { label: 'Every 20 minutes', value: '20' },
          { label: 'Every 30 minutes', value: '30' },
          { label: 'Every hour', value: '60' },
        ],
      },
      {
        name: 'contentSyncEnabled',
        type: 'boolean',
        label: 'Sync Page Content',
        value: s.config.contentSyncEnabled,
      },
      {
        name: 'maxPagesPerContentSync',
        type: 'select',
        label: 'Pages Per Content Sync',
        value: s.config.maxPagesPerContentSync.toString(),
        options: [
          { label: '25 pages', value: '25' },
          { label: '50 pages', value: '50' },
          { label: '100 pages', value: '100' },
        ],
      },
    ],
  };
}

function onSetOption(args: { name: string; value: unknown }): void {
  const s = globalThis.getNotionSkillState();
  const credential = oauth.getCredential();

  switch (args.name) {
    case 'syncInterval':
      s.config.syncIntervalMinutes = parseInt(args.value as string, 10);
      if (credential) {
        cron.unregister('notion-sync');
        const cronExpr = `0 */${s.config.syncIntervalMinutes} * * * *`;
        cron.register('notion-sync', cronExpr);
      }
      break;

    case 'contentSyncEnabled':
      s.config.contentSyncEnabled = Boolean(args.value);
      break;

    case 'maxPagesPerContentSync':
      s.config.maxPagesPerContentSync = parseInt(args.value as string, 10);
      break;
  }

  state.set('config', s.config);
  publishState();
}

// ---------------------------------------------------------------------------
// State publishing
// ---------------------------------------------------------------------------

function publishState(): void {
  const s = globalThis.getNotionSkillState();

  state.setPartial({
    connected: !!oauth.getCredential(),
    workspaceName: s.config.workspaceName || null,
    syncInProgress: s.syncStatus.syncInProgress,
    lastSyncTime: s.syncStatus.lastSyncTime
      ? new Date(s.syncStatus.lastSyncTime).toISOString()
      : null,
    totalPages: s.syncStatus.totalPages,
    totalDatabases: s.syncStatus.totalDatabases,
    totalUsers: s.syncStatus.totalUsers,
    pagesWithContent: s.syncStatus.pagesWithContent,
    pagesWithSummary: s.syncStatus.pagesWithSummary,
    lastSyncError: s.syncStatus.lastSyncError,
  });
}

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------

tools = [
  // Pages
  searchTool,
  getPageTool,
  createPageTool,
  updatePageTool,
  deletePageTool,
  getPageContentTool,
  listAllPagesTool,
  appendTextTool,
  // Databases
  queryDatabaseTool,
  getDatabaseTool,
  createDatabaseTool,
  updateDatabaseTool,
  listAllDatabasesTool,
  // Blocks
  getBlockTool,
  getBlockChildrenTool,
  appendBlocksTool,
  updateBlockTool,
  deleteBlockTool,
  // Users
  listUsersTool,
  getUserTool,
  // Comments
  createCommentTool,
  listCommentsTool,
  // Local sync tools
  searchLocalTool,
  syncStatusTool,
  syncNowTool,
  // AI tools
  summarizePagesTool,
];

// ---------------------------------------------------------------------------
// Expose lifecycle hooks on globalThis so the REPL/runtime can call them.
// esbuild IIFE bundling traps function declarations in the closure scope —
// without explicit assignment they are unreachable from outside.
// ---------------------------------------------------------------------------

_g.init = init;
_g.start = start;
_g.stop = stop;
_g.onCronTrigger = onCronTrigger;
_g.onSessionStart = onSessionStart;
_g.onSessionEnd = onSessionEnd;
_g.onOAuthComplete = onOAuthComplete;
_g.onOAuthRevoked = onOAuthRevoked;
_g.onDisconnect = onDisconnect;
_g.onListOptions = onListOptions;
_g.onSetOption = onSetOption;
_g.publishState = publishState;
