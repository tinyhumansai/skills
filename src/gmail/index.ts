// Gmail skill main entry point
// Gmail integration with OAuth bridge, email management, and real-time sync
import { getSyncState, setSyncState } from './db/helpers';
import { initializeGmailSchema } from './db/schema';
import { getGmailSkillState } from './state';
import { isSyncCompleted, onSync, performInitialSync } from './sync';
import { tools } from './tools';
import type { SkillConfig } from './types';

// ---------------------------------------------------------------------------
// Gmail API helper: uses access token from frontend when present, else oauth.fetch proxy.
// ---------------------------------------------------------------------------
const GMAIL_API_BASE = 'https://gmail.googleapis.com/gmail/v1';

async function gmailFetch(
  endpoint: string,
  options: {
    method?: string;
    body?: string;
    headers?: Record<string, string>;
    timeout?: number;
  } = {}
): Promise<{ success: boolean; data?: any; error?: { code: number; message: string } }> {
  const credential = oauth.getCredential();

  if (!credential) {
    console.log('[gmail] gmailFetch: no credential (OAuth not connected)');
    return {
      success: false,
      error: { code: 401, message: 'Gmail not connected. Complete OAuth setup first.' },
    };
  }

  const method = options.method || 'GET';
  const path = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
  const url = GMAIL_API_BASE + path;

  const useAccessToken = !!credential.accessToken;

  console.log(
    `[gmail] gmailFetch: path=${path} method=${method} useAccessToken=${useAccessToken} credentialId=${credential.credentialId || '(none)'}`
  );

  try {
    let response: { status: number; headers: Record<string, string>; body: string };

    if (useAccessToken) {
      const res = await net.fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${credential.accessToken}`,
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
        body: options.body,
        timeout: options.timeout || 30,
      });
      response = res;
    } else {
      response = await oauth.fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        body: options.body,
        timeout: options.timeout || 30,
      });
    }

    const s = getGmailSkillState();

    if (response.status === 401) {
      const bodyPreview = response.body ? response.body.slice(0, 200) : '(empty)';
      console.log(`[gmail] gmailFetch: 401 Unauthorized path=${path} body=${bodyPreview}`);
    } else if (response.status >= 400) {
      const bodyPreview = response.body ? response.body.slice(0, 200) : '(empty)';
      console.log(
        `[gmail] gmailFetch: error path=${path} status=${response.status} body=${bodyPreview}`
      );
    }

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
    }
    const error = response.body
      ? JSON.parse(response.body)
      : { code: response.status, message: 'API request failed' };
    s.lastApiError = error.message || `HTTP ${response.status}`;
    return { success: false, error };
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    const s = getGmailSkillState();
    s.lastApiError = errorMsg;
    return { success: false, error: { code: 500, message: errorMsg } };
  }
}

// ---------------------------------------------------------------------------
// Lifecycle hooks
// ---------------------------------------------------------------------------

async function init(): Promise<void> {
  console.log(`[gmail] Initializing on ${platform.os()}`);
  const s = getGmailSkillState();

  // Initialize database schema
  initializeGmailSchema();

  // Load persisted config from store
  const saved = state.get('config') as Partial<SkillConfig> | null;
  if (saved) {
    s.config.credentialId = saved.credentialId || s.config.credentialId;
    s.config.userEmail = saved.userEmail || s.config.userEmail;
    s.config.syncEnabled = saved.syncEnabled ?? s.config.syncEnabled;
    s.config.syncIntervalMinutes = saved.syncIntervalMinutes || s.config.syncIntervalMinutes;
    s.config.maxEmailsPerSync = saved.maxEmailsPerSync || s.config.maxEmailsPerSync;
    s.config.notifyOnNewEmails = saved.notifyOnNewEmails ?? s.config.notifyOnNewEmails;
    s.config.showSensitiveMessages = saved.showSensitiveMessages ?? s.config.showSensitiveMessages;
  }

  // Load sync status
  const lastSync = getSyncState('last_sync_time');
  const lastHistoryId = getSyncState('last_history_id');
  if (lastSync) s.syncStatus.lastSyncTime = parseInt(lastSync, 10);
  if (lastHistoryId) s.syncStatus.lastHistoryId = lastHistoryId;

  const isConnected = !!oauth.getCredential();
  console.log(`[gmail] Initialized. Connected: ${isConnected}`);
}

async function start(): Promise<void> {
  console.log('[gmail] Starting skill...');
  const s = getGmailSkillState();
  const credential = oauth.getCredential();

  if (credential && s.config.syncEnabled) {
    // Schedule periodic sync
    const cronExpr = `0 */${s.config.syncIntervalMinutes} * * * *`;
    cron.register('gmail-sync', cronExpr);
    console.log(`[gmail] Scheduled sync every ${s.config.syncIntervalMinutes} minutes`);

    // Load Gmail profile
    loadGmailProfile();

    // Run initial sync if not yet completed
    if (!isSyncCompleted()) {
      console.log('[gmail] Initial sync not completed, starting...');
      performInitialSync((msg, pct) => {
        console.log(`[gmail] Sync progress: ${msg} (${pct}%)`);
      });
    }

    // Publish initial state
    publishSkillState();
  } else {
    console.log('[gmail] Not connected or sync disabled');
  }
}

async function stop(): Promise<void> {
  console.log('[gmail] Stopping skill...');
  const s = getGmailSkillState();

  // Unregister cron schedules
  cron.unregister('gmail-sync');

  // Save current state
  state.set('config', s.config);

  setSyncState('last_sync_time', s.syncStatus.lastSyncTime.toString());
  setSyncState('last_history_id', s.syncStatus.lastHistoryId);

  console.log('[gmail] Skill stopped');
}

async function onCronTrigger(scheduleId: string): Promise<void> {
  console.log(`[gmail] Cron triggered: ${scheduleId}`);
  if (scheduleId === 'gmail-sync') {
    await onSync();
  }
}

async function onSessionStart(args: { sessionId: string }): Promise<void> {
  const s = getGmailSkillState();
  s.activeSessions.push(args.sessionId);
  console.log(`[gmail] Session started: ${args.sessionId} (${s.activeSessions.length} active)`);
}

async function onSessionEnd(args: { sessionId: string }): Promise<void> {
  const s = getGmailSkillState();
  const index = s.activeSessions.indexOf(args.sessionId);
  if (index > -1) {
    s.activeSessions.splice(index, 1);
  }
  console.log(`[gmail] Session ended: ${args.sessionId} (${s.activeSessions.length} active)`);
}

// ---------------------------------------------------------------------------
// OAuth lifecycle hooks
// ---------------------------------------------------------------------------

async function onOAuthComplete(args: OAuthCompleteArgs): Promise<OAuthCompleteResult | void> {
  console.log(`[gmail] OAuth complete for provider: ${args.provider}`);
  const s = getGmailSkillState();

  s.config.credentialId = args.credentialId;
  if (args.accountLabel) {
    s.config.userEmail = args.accountLabel;
  }

  state.set('config', s.config);

  // Load profile to get user email
  loadGmailProfile();

  publishSkillState();
  console.log(`[gmail] Connected as ${s.config.userEmail || args.accountLabel || 'unknown'}`);
}

async function onOAuthRevoked(args: OAuthRevokedArgs): Promise<void> {
  console.log(`[gmail] OAuth revoked: ${args.reason}`);
  const s = getGmailSkillState();

  s.config.credentialId = '';
  s.config.userEmail = '';
  s.profile = null;

  state.set('config', s.config);
  cron.unregister('gmail-sync');
  publishSkillState();

  if (args.reason === 'token_expired' || args.reason === 'provider_revoked') {
    platform.notify('Gmail Disconnected', 'Your Gmail connection has expired. Please reconnect.');
  }
}

async function onDisconnect(): Promise<void> {
  console.log('[gmail] Disconnecting...');
  const s = getGmailSkillState();

  // Revoke via OAuth bridge
  oauth.revoke();

  // Reset configuration
  s.config = {
    credentialId: '',
    userEmail: '',
    syncEnabled: true,
    syncIntervalMinutes: 15,
    maxEmailsPerSync: 10,
    notifyOnNewEmails: true,
  };

  s.profile = null;
  state.delete('config');
  cron.unregister('gmail-sync');
  publishSkillState();

  console.log('[gmail] Disconnected and cleaned up');
}

// ---------------------------------------------------------------------------
// Options system
// ---------------------------------------------------------------------------

async function onListOptions(): Promise<{ options: SkillOption[] }> {
  const s = getGmailSkillState();

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
      {
        name: 'showSensitiveMessages',
        type: 'boolean',
        label: 'Show Sensitive Messages',
        value: s.config.showSensitiveMessages ?? false,
      },
    ],
  };
}

async function onSetOption(args: { name: string; value: unknown }): Promise<void> {
  const s = getGmailSkillState();
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

    case 'showSensitiveMessages':
      s.config.showSensitiveMessages = Boolean(args.value);
      break;
  }

  // Save updated config
  state.set('config', s.config);
  publishSkillState();
}

// ---------------------------------------------------------------------------
// Skill export
// ---------------------------------------------------------------------------

async function loadGmailProfile(): Promise<void> {
  const response = await gmailFetch('/users/me/profile');
  if (response.success) {
    const s = getGmailSkillState();
    s.profile = {
      emailAddress: response.data.emailAddress,
      messagesTotal: response.data.messagesTotal || 0,
      threadsTotal: response.data.threadsTotal || 0,
      historyId: response.data.historyId,
    };

    if (!s.config.userEmail) {
      s.config.userEmail = response.data.emailAddress;
      state.set('config', s.config);
    }

    console.log(`[gmail] Profile loaded for ${s.profile.emailAddress}`);
    publishSkillState();
  }
}

/**
 * Perform email sync using the OAuth credential (access token) via gmailFetch/oauth.fetch.
 * Called on start(), onOAuthComplete(), and by cron; frontend does not run its own sync.
 */
async function performSync(): Promise<void> {
  const s = getGmailSkillState();

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

    const response = await gmailFetch(`/users/me/messages?${params.join('&')}`);

    if (response.success && response.data.messages) {
      let newEmails = 0;

      for (const msgRef of response.data.messages) {
        const msgResponse = await gmailFetch(`/users/me/messages/${msgRef.id}`);
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
  const s = getGmailSkillState();
  const credential = oauth.getCredential();
  const isConnected = !!credential;

  // Profile and emails for frontend gmail store (gmailSlice) — only when connected
  const profile =
    isConnected && s.profile != null
      ? {
          email_address: s.profile.emailAddress,
          messages_total: s.profile.messagesTotal,
          threads_total: s.profile.threadsTotal,
          history_id: s.profile.historyId,
        }
      : null;

  let emails: Array<{
    id: string;
    threadId: string;
    snippet?: string;
    subject?: string;
    from?: string;
    date?: string;
  }> = [];
  if (isConnected) {
    const getEmailsFromDb = (
      globalThis as {
        getEmails?: (opts: {
          maxResults?: number;
        }) => Array<{
          id: string;
          thread_id: string;
          subject: string;
          sender_email: string;
          date: number;
          snippet: string;
        }>;
      }
    ).getEmails;
    if (getEmailsFromDb) {
      const rows = getEmailsFromDb({ maxResults: s.config.maxEmailsPerSync });
      emails = rows.map(row => ({
        id: row.id,
        threadId: row.thread_id,
        snippet: row.snippet || undefined,
        subject: row.subject || undefined,
        from: row.sender_email || undefined,
        date: row.date ? new Date(row.date).toISOString() : undefined,
      }));
      s.syncStatus.totalEmails = s.profile?.messagesTotal ?? rows.length;
    }
  }

  state.setPartial({
    // Standard SkillHostConnectionState fields
    connection_status: isConnected ? 'connected' : 'disconnected',
    auth_status: isConnected ? 'authenticated' : 'not_authenticated',
    connection_error: s.lastApiError || null,
    auth_error: null,
    is_initialized: isConnected,
    // Skill-specific fields
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
    // For frontend gmail store (gmailSlice)
    profile,
    emails,
  });
}

// Expose helper functions on globalThis for tools to use
const _g = globalThis as Record<string, unknown>;
_g.getGmailSkillState = getGmailSkillState;
_g.gmailFetch = gmailFetch;
_g.performSync = performSync;
_g.publishSkillState = publishSkillState;
_g.loadGmailProfile = loadGmailProfile;

const skill: Skill = {
  info: {
    id: 'gmail',
    name: 'Gmail',
    version: '2.1.0',
    description: 'Gmail integration with persistent storage',
    auto_start: false,
    setup: { required: true, label: 'Configure Gmail' },
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
  onSync,
  onDisconnect,
  onListOptions,
  onSetOption,
};

export default skill;
