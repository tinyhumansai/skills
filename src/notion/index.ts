// notion/index.ts
// Notion integration skill exposing 25 tools for the Notion API + local sync.
// Supports pages, databases, blocks, users, comments, and local search.
// Authentication is handled via the platform OAuth bridge.
import { notionApi } from './api/index';
import { getEntityCounts, getLocalPages } from './db/helpers';
import { initializeNotionSchema } from './db/schema';
import { formatUserSummary } from './helpers';
import { getNotionSkillState } from './state';
import type { NotionSkillConfig } from './state';
import { performSync } from './sync';
import tools from './tools/index';

async function init(): Promise<void> {
  console.log('[notion] Initializing');
  const s = getNotionSkillState();

  initializeNotionSchema();

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

  // Load sync state from store (lastSyncTime may be an ISO string from
  // setPartial or a number from legacy last_sync_time; parse tolerantly)
  const lastSync = state.get('lastSyncTime') as string | number | null;
  if (lastSync) {
    s.syncStatus.lastSyncTime =
      typeof lastSync === 'number' ? lastSync : new Date(lastSync).getTime();
  }

  const counts = getEntityCounts();
  s.syncStatus.totalPages = counts.pages;
  s.syncStatus.totalDatabases = counts.databases;
  s.syncStatus.totalDatabaseRows = counts.databaseRows;
  s.syncStatus.pagesWithContent = counts.pagesWithContent;
  s.syncStatus.pagesWithSummary = counts.pagesWithSummary;

  const cred = oauth.getCredential();
  if (cred) {
    s.config.credentialId = cred.credentialId;
    console.log(`[notion] Connected to workspace: ${s.config.workspaceName || '(unnamed)'}`);
  } else {
    console.log('[notion] No OAuth credential — waiting for setup');
  }

  publishState();
}

async function start(): Promise<void> {
  const s = getNotionSkillState();

  if (!oauth.getCredential()) {
    console.log('[notion] No credential — skill inactive until OAuth completes');
    return;
  }

  // Register sync cron schedule
  const cronExpr = `0 */${s.config.syncIntervalMinutes} * * * *`;
  cron.register('notion-sync', cronExpr);
  console.log(`[notion] Scheduled sync every ${s.config.syncIntervalMinutes} minutes`);
}

async function stop(): Promise<void> {
  console.log('[notion] Stopping');
  const s = getNotionSkillState();

  // Unregister cron
  cron.unregister('notion-sync');

  // Persist config
  state.set('config', s.config);
  state.set('status', 'stopped');
  console.log('[notion] Stopped');
}

async function onCronTrigger(scheduleId: string): Promise<void> {
  console.log(`[notion] Cron triggered: ${scheduleId}`);

  if (scheduleId === 'notion-sync') {
    performSync();
  }
}

// ---------------------------------------------------------------------------
// Session lifecycle
// ---------------------------------------------------------------------------

async function onSessionStart(args: { sessionId: string }): Promise<void> {
  const s = getNotionSkillState();
  s.activeSessions.push(args.sessionId);
}

async function onSessionEnd(args: { sessionId: string }): Promise<void> {
  const s = getNotionSkillState();
  const index = s.activeSessions.indexOf(args.sessionId);
  if (index > -1) {
    s.activeSessions.splice(index, 1);
  }
}

// ---------------------------------------------------------------------------
// OAuth lifecycle
// ---------------------------------------------------------------------------

async function onOAuthComplete(args: OAuthCompleteArgs): Promise<OAuthCompleteResult | void> {
  const s = getNotionSkillState();
  s.config.credentialId = args.credentialId;
  console.log(
    `[notion] OAuth complete — credential: ${args.credentialId}, account: ${args.accountLabel || '(unknown)'}`
  );

  if (args.accountLabel) {
    s.config.workspaceName = args.accountLabel;
  }

  state.set('config', s.config);

  // Start sync schedule
  const cronExpr = `0 */${s.config.syncIntervalMinutes} * * * *`;
  cron.register('notion-sync', cronExpr);

  publishState();
}

async function onOAuthRevoked(args: OAuthRevokedArgs): Promise<void> {
  console.log(`[notion] OAuth revoked — reason: ${args.reason}`);
  const s = getNotionSkillState();

  s.config.credentialId = '';
  s.config.workspaceName = '';
  state.delete('config');
  cron.unregister('notion-sync');
  publishState();
}

async function onDisconnect(): Promise<void> {
  console.log('[notion] Disconnecting');
  const s = getNotionSkillState();

  oauth.revoke();
  s.config.credentialId = '';
  s.config.workspaceName = '';
  state.delete('config');
  cron.unregister('notion-sync');
  publishState();
}

async function onSync(): Promise<void> {
  console.log('[notion] Syncing');

  // Fetch the Notion profile immediately and publish it into state so the
  // workspace/user context is available to the host.
  try {
    const user = await notionApi.getUser('me');
    const profile = formatUserSummary(user as Record<string, unknown>);
    state.setPartial({ profile });
  } catch (e) {
    console.error('[notion] Failed to fetch profile on OAuth complete:', e);
  }

  publishState();

  performSync();
}

// ---------------------------------------------------------------------------
// Options system
// ---------------------------------------------------------------------------

async function onListOptions(): Promise<{ options: SkillOption[] }> {
  const s = getNotionSkillState();

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

async function onSetOption(args: { name: string; value: unknown }): Promise<void> {
  const s = getNotionSkillState();
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

async function publishState(): Promise<void> {
  const s = getNotionSkillState();
  const isConnected = !!oauth.getCredential();

  // Fetch recent pages from local DB (populated after sync)
  let pages: Array<{
    id: string;
    title: string;
    url: string | null;
    last_edited_time: string;
    content_text: string | null;
  }> = [];
  if (isConnected) {
    try {
      const localPages = getLocalPages({ limit: 100 });
      pages = localPages.map(p => ({
        id: p.id,
        title: p.title,
        url: p.url,
        last_edited_time: p.last_edited_time,
        content_text: p.content_text,
      }));
    } catch (e) {
      console.error('[notion] publishState: failed to load local pages:', e);
    }
  }

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
    totalPages: s.syncStatus.totalPages,
    totalDatabases: s.syncStatus.totalDatabases,
    totalDatabaseRows: s.syncStatus.totalDatabaseRows,
    pagesWithContent: s.syncStatus.pagesWithContent,
    pagesWithSummary: s.syncStatus.pagesWithSummary,
    lastSyncError: s.syncStatus.lastSyncError,
    pages,
  });
}

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Expose lifecycle hooks on globalThis so the REPL/runtime can call them.
// esbuild IIFE bundling traps function declarations in the closure scope —
// without explicit assignment they are unreachable from outside.
// ---------------------------------------------------------------------------

async function onPing(): Promise<PingResult> {
  const cred = oauth.getCredential();
  if (!cred) {
    return { ok: false, errorType: 'auth', errorMessage: 'No OAuth credential' };
  }
  try {
    const response = await oauth.fetch('/v1/users?page_size=1');
    console.log('[notion] onPing response: ', response.body);
    if (response.status === 401 || response.status === 403) {
      return { ok: false, errorType: 'auth', errorMessage: `Notion returned ${response.status}` };
    }
    if (response.status >= 400) {
      return {
        ok: false,
        errorType: 'network',
        errorMessage: `Notion returned ${response.status}`,
      };
    }
    return { ok: true };
  } catch (err) {
    return { ok: false, errorType: 'network', errorMessage: String(err) };
  }
}

const skill: Skill = {
  info: {
    id: 'notion',
    name: 'Notion',
    version: '2.1.0', // Bumped for persistent storage
    description: 'Notion integration with persistent storage',
    auto_start: false,
    setup: { required: true, label: 'Configure Notion' },
  },
  tools,
  init,
  start,
  stop,
  onCronTrigger,
  onSessionStart,
  onSessionEnd,
  onOAuthComplete,
  onOAuthRevoked,
  onDisconnect,
  onSync,
  onListOptions,
  onSetOption,
  publishState,
  onPing,
};

// Expose skill for QuickJS runtime (extract_tools and start_async_tool_call read globalThis.__skill.default.tools)
const g = globalThis as Record<string, unknown>;
if (typeof g.__skill === 'undefined') {
  g.__skill = { default: skill };
}

export default skill;
