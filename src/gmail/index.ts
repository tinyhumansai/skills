// Gmail skill main entry point
// Gmail integration with OAuth bridge, email management, and real-time sync
// Import all tools
import './db-helpers';
import './db-schema';
// Import modules to initialize state and expose functions on globalThis
import './skill-state';
import { getEmailTool } from './tools/get-email';
import { getEmailsTool } from './tools/get-emails';
import { getLabelsTool } from './tools/get-labels';
import { getProfileTool } from './tools/get-profile';
import { markEmailTool } from './tools/mark-email';
import { searchEmailsTool } from './tools/search-emails';
import { sendEmailTool } from './tools/send-email';
import type { SkillConfig } from './types';

// ---------------------------------------------------------------------------
// Gmail API helper (uses oauth.fetch proxy)
// ---------------------------------------------------------------------------

function gmailFetch(
  endpoint: string,
  options: {
    method?: string;
    body?: string;
    headers?: Record<string, string>;
    timeout?: number;
  } = {}
): { success: boolean; data?: any; error?: { code: number; message: string } } {
  const credential = oauth.getCredential();
  if (!credential) {
    return {
      success: false,
      error: { code: 401, message: 'Gmail not connected. Complete OAuth setup first.' },
    };
  }

  try {
    const response = oauth.fetch(endpoint, {
      method: options.method || 'GET',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      body: options.body,
      timeout: options.timeout || 30,
    });

    const s = globalThis.getGmailSkillState();

    // Update rate limit info from headers
    if (response.headers['x-ratelimit-remaining']) {
      s.rateLimitRemaining = parseInt(response.headers['x-ratelimit-remaining'], 10);
    }
    if (response.headers['x-ratelimit-reset']) {
      s.rateLimitReset = parseInt(response.headers['x-ratelimit-reset'], 10) * 1000;
    }

    if (response.status >= 200 && response.status < 300) {
      const data = response.body ? JSON.parse(response.body) : null;
      s.lastApiError = null;
      return { success: true, data };
    } else {
      const error = response.body
        ? JSON.parse(response.body)
        : { code: response.status, message: 'API request failed' };
      s.lastApiError = error.message || `HTTP ${response.status}`;
      return { success: false, error };
    }
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    const s = globalThis.getGmailSkillState();
    s.lastApiError = errorMsg;
    return { success: false, error: { code: 500, message: errorMsg } };
  }
}

// ---------------------------------------------------------------------------
// Lifecycle hooks
// ---------------------------------------------------------------------------

function init(): void {
  console.log(`[gmail] Initializing on ${platform.os()}`);
  const s = globalThis.getGmailSkillState();

  // Initialize database schema
  const initSchema = (globalThis as { initializeGmailSchema?: () => void }).initializeGmailSchema;
  if (initSchema) {
    initSchema();
  }

  // Load persisted config from store
  const saved = store.get('config') as Partial<SkillConfig> | null;
  if (saved) {
    s.config.credentialId = saved.credentialId || s.config.credentialId;
    s.config.userEmail = saved.userEmail || s.config.userEmail;
    s.config.syncEnabled = saved.syncEnabled ?? s.config.syncEnabled;
    s.config.syncIntervalMinutes = saved.syncIntervalMinutes || s.config.syncIntervalMinutes;
    s.config.maxEmailsPerSync = saved.maxEmailsPerSync || s.config.maxEmailsPerSync;
    s.config.notifyOnNewEmails = saved.notifyOnNewEmails ?? s.config.notifyOnNewEmails;
  }

  // Load sync status
  const getSyncState = (globalThis as { getSyncState?: (key: string) => string | null })
    .getSyncState;
  if (getSyncState) {
    const lastSync = getSyncState('last_sync_time');
    const lastHistoryId = getSyncState('last_history_id');
    if (lastSync) s.syncStatus.lastSyncTime = parseInt(lastSync, 10);
    if (lastHistoryId) s.syncStatus.lastHistoryId = lastHistoryId;
  }

  const isConnected = !!oauth.getCredential();
  console.log(`[gmail] Initialized. Connected: ${isConnected}`);
}

function start(): void {
  console.log('[gmail] Starting skill...');
  const s = globalThis.getGmailSkillState();
  const credential = oauth.getCredential();

  if (credential && s.config.syncEnabled) {
    // Schedule periodic sync
    const cronExpr = `0 */${s.config.syncIntervalMinutes} * * * *`;
    cron.register('gmail-sync', cronExpr);
    console.log(`[gmail] Scheduled sync every ${s.config.syncIntervalMinutes} minutes`);

    // Load Gmail profile
    loadGmailProfile();

    // Perform initial sync
    performSync();

    // Publish initial state
    publishSkillState();
  } else {
    console.log('[gmail] Not connected or sync disabled');
  }
}

function stop(): void {
  console.log('[gmail] Stopping skill...');
  const s = globalThis.getGmailSkillState();

  // Unregister cron schedules
  cron.unregister('gmail-sync');

  // Save current state
  store.set('config', s.config);

  const setSyncState = (globalThis as { setSyncState?: (key: string, value: string) => void })
    .setSyncState;
  if (setSyncState) {
    setSyncState('last_sync_time', s.syncStatus.lastSyncTime.toString());
    setSyncState('last_history_id', s.syncStatus.lastHistoryId);
  }

  console.log('[gmail] Skill stopped');
}

function onCronTrigger(scheduleId: string): void {
  console.log(`[gmail] Cron triggered: ${scheduleId}`);

  if (scheduleId === 'gmail-sync') {
    performSync();
  }
}

function onSessionStart(args: { sessionId: string }): void {
  const s = globalThis.getGmailSkillState();
  s.activeSessions.push(args.sessionId);
  console.log(`[gmail] Session started: ${args.sessionId} (${s.activeSessions.length} active)`);
}

function onSessionEnd(args: { sessionId: string }): void {
  const s = globalThis.getGmailSkillState();
  const index = s.activeSessions.indexOf(args.sessionId);
  if (index > -1) {
    s.activeSessions.splice(index, 1);
  }
  console.log(`[gmail] Session ended: ${args.sessionId} (${s.activeSessions.length} active)`);
}

// ---------------------------------------------------------------------------
// OAuth lifecycle hooks
// ---------------------------------------------------------------------------

function onOAuthComplete(args: OAuthCompleteArgs): OAuthCompleteResult | void {
  console.log(`[gmail] OAuth complete for provider: ${args.provider}`);
  const s = globalThis.getGmailSkillState();

  s.config.credentialId = args.credentialId;
  if (args.accountLabel) {
    s.config.userEmail = args.accountLabel;
  }

  store.set('config', s.config);

  // Load profile to get user email
  loadGmailProfile();

  // Start sync
  if (s.config.syncEnabled) {
    const cronExpr = `0 */${s.config.syncIntervalMinutes} * * * *`;
    cron.register('gmail-sync', cronExpr);
    performSync();
  }

  publishSkillState();
  console.log(`[gmail] Connected as ${s.config.userEmail || args.accountLabel || 'unknown'}`);
}

function onOAuthRevoked(args: OAuthRevokedArgs): void {
  console.log(`[gmail] OAuth revoked: ${args.reason}`);
  const s = globalThis.getGmailSkillState();

  s.config.credentialId = '';
  s.config.userEmail = '';
  s.profile = null;

  store.set('config', s.config);
  cron.unregister('gmail-sync');
  publishSkillState();

  if (args.reason === 'token_expired' || args.reason === 'provider_revoked') {
    platform.notify('Gmail Disconnected', 'Your Gmail connection has expired. Please reconnect.');
  }
}

function onDisconnect(): void {
  console.log('[gmail] Disconnecting...');
  const s = globalThis.getGmailSkillState();

  // Revoke via OAuth bridge
  oauth.revoke();

  // Reset configuration
  s.config = {
    credentialId: '',
    userEmail: '',
    syncEnabled: true,
    syncIntervalMinutes: 15,
    maxEmailsPerSync: 100,
    notifyOnNewEmails: true,
  };

  s.profile = null;
  store.delete('config');
  cron.unregister('gmail-sync');
  publishSkillState();

  console.log('[gmail] Disconnected and cleaned up');
}

// ---------------------------------------------------------------------------
// Options system
// ---------------------------------------------------------------------------

function onListOptions(): { options: SkillOption[] } {
  const s = globalThis.getGmailSkillState();

  return {
    options: [
      {
        name: 'syncEnabled',
        type: 'boolean',
        label: 'Enable Email Sync',
        value: s.config.syncEnabled,
      },
      {
        name: 'syncInterval',
        type: 'select',
        label: 'Sync Interval',
        value: s.config.syncIntervalMinutes.toString(),
        options: [
          { label: 'Every 5 minutes', value: '5' },
          { label: 'Every 15 minutes', value: '15' },
          { label: 'Every 30 minutes', value: '30' },
          { label: 'Every hour', value: '60' },
        ],
      },
      {
        name: 'maxEmailsPerSync',
        type: 'select',
        label: 'Max Emails Per Sync',
        value: s.config.maxEmailsPerSync.toString(),
        options: [
          { label: '50 emails', value: '50' },
          { label: '100 emails', value: '100' },
          { label: '250 emails', value: '250' },
          { label: '500 emails', value: '500' },
        ],
      },
      {
        name: 'notifyOnNewEmails',
        type: 'boolean',
        label: 'Notify on New Emails',
        value: s.config.notifyOnNewEmails,
      },
    ],
  };
}

function onSetOption(args: { name: string; value: unknown }): void {
  const s = globalThis.getGmailSkillState();
  const credential = oauth.getCredential();

  switch (args.name) {
    case 'syncEnabled':
      s.config.syncEnabled = Boolean(args.value);
      if (s.config.syncEnabled && credential) {
        const cronExpr = `0 */${s.config.syncIntervalMinutes} * * * *`;
        cron.register('gmail-sync', cronExpr);
      } else {
        cron.unregister('gmail-sync');
      }
      break;

    case 'syncInterval':
      s.config.syncIntervalMinutes = parseInt(args.value as string, 10);
      if (s.config.syncEnabled && credential) {
        cron.unregister('gmail-sync');
        const cronExpr = `0 */${s.config.syncIntervalMinutes} * * * *`;
        cron.register('gmail-sync', cronExpr);
      }
      break;

    case 'maxEmailsPerSync':
      s.config.maxEmailsPerSync = parseInt(args.value as string, 10);
      break;

    case 'notifyOnNewEmails':
      s.config.notifyOnNewEmails = Boolean(args.value);
      break;
  }

  // Save updated config
  store.set('config', s.config);
  publishSkillState();
}

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

function loadGmailProfile(): void {
  const response = gmailFetch('/users/me/profile');
  if (response.success) {
    const s = globalThis.getGmailSkillState();
    s.profile = {
      emailAddress: response.data.emailAddress,
      messagesTotal: response.data.messagesTotal || 0,
      threadsTotal: response.data.threadsTotal || 0,
      historyId: response.data.historyId,
    };

    if (!s.config.userEmail) {
      s.config.userEmail = response.data.emailAddress;
      store.set('config', s.config);
    }

    console.log(`[gmail] Profile loaded for ${s.profile.emailAddress}`);
  }
}

function performSync(): void {
  const s = globalThis.getGmailSkillState();

  if (!oauth.getCredential() || s.syncStatus.syncInProgress) {
    return;
  }

  console.log('[gmail] Starting email sync...');
  s.syncStatus.syncInProgress = true;
  s.syncStatus.newEmailsCount = 0;

  const upsertEmail = (globalThis as { upsertEmail?: (msg: any) => void }).upsertEmail;
  if (!upsertEmail) return;

  try {
    // Get recent messages
    const params: string[] = [];
    params.push(`maxResults=${s.config.maxEmailsPerSync}`);
    params.push('q=in%3Ainbox');

    const response = gmailFetch(`/users/me/messages?${params.join('&')}`);

    if (response.success && response.data.messages) {
      let newEmails = 0;

      for (const msgRef of response.data.messages) {
        const msgResponse = gmailFetch(`/users/me/messages/${msgRef.id}`);
        if (msgResponse.success) {
          upsertEmail(msgResponse.data);
          newEmails++;
        }
      }

      s.syncStatus.newEmailsCount = newEmails;

      if (newEmails > 0 && s.config.notifyOnNewEmails) {
        platform.notify('Gmail Sync Complete', `Synchronized ${newEmails} emails`);
      }
    }

    s.syncStatus.lastSyncTime = Date.now();
    s.syncStatus.nextSyncTime = Date.now() + s.config.syncIntervalMinutes * 60 * 1000;

    console.log(`[gmail] Sync completed. New emails: ${s.syncStatus.newEmailsCount}`);
  } catch (error) {
    console.error(`[gmail] Sync failed: ${error}`);
    s.lastApiError = error instanceof Error ? error.message : String(error);
  } finally {
    s.syncStatus.syncInProgress = false;
    publishSkillState();
  }
}

function publishSkillState(): void {
  const s = globalThis.getGmailSkillState();
  const credential = oauth.getCredential();

  state.setPartial({
    connected: !!credential,
    userEmail: s.config.userEmail,
    syncEnabled: s.config.syncEnabled,
    syncInProgress: s.syncStatus.syncInProgress,
    lastSyncTime: new Date(s.syncStatus.lastSyncTime).toISOString(),
    nextSyncTime: new Date(s.syncStatus.nextSyncTime).toISOString(),
    totalEmails: s.syncStatus.totalEmails,
    newEmailsCount: s.syncStatus.newEmailsCount,
    activeSessions: s.activeSessions.length,
    rateLimitRemaining: s.rateLimitRemaining,
    lastError: s.lastApiError,
  });
}

// Expose helper functions on globalThis for tools to use
const _g = globalThis as Record<string, unknown>;
_g.gmailFetch = gmailFetch;
_g.performSync = performSync;
_g.publishSkillState = publishSkillState;
_g.loadGmailProfile = loadGmailProfile;

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------

tools = [
  getEmailsTool,
  sendEmailTool,
  getEmailTool,
  getLabelsTool,
  searchEmailsTool,
  markEmailTool,
  getProfileTool,
];

// Expose lifecycle hooks on globalThis so the REPL/runtime can call them.
// esbuild IIFE bundling traps function declarations in the closure scope.
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
