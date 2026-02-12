// telegram/index.ts
// Telegram integration skill using TDLib via V8 runtime.
// Provides tools for Telegram API access with native TDLib bindings.
// Import skill state (initializes globalThis.getTelegramSkillState)
// registers globalThis.initializeTelegramSchema
// Import TDLib client wrapper - this also assigns TdLibClient to globalThis
// registers globalThis.telegramDispatchUpdate
import { getMe } from './api';
import './db/helpers';
import './db/schema';
import { createSetupHandlers } from './setup';
import type { AuthorizationState } from './state';
import './sync';
import type { TdLibClient as TdLibClientType, TdUpdate, TdUser } from './tdlib-client';
import tools from './tools/index';
import './update-handlers';

// Access TdLibClient from globalThis (workaround for esbuild bundling issues)
const getTdLibClientClass = (): typeof TdLibClientType => {
  const cls = (globalThis as Record<string, unknown>).TdLibClient as typeof TdLibClientType;
  if (!cls) {
    throw new Error('TdLibClient not available on globalThis');
  }
  return cls;
};

// Runtime globals (store, state, platform, db, cron, tools) are declared in types/globals.d.ts

// ---------------------------------------------------------------------------
// Authorization State Helpers
// ---------------------------------------------------------------------------

/**
 * Parse TDLib authorization state update to our simplified state type.
 */
function parseAuthState(update: TdUpdate): AuthorizationState {
  const stateType = (update as { authorization_state?: { '@type': string } }).authorization_state?.[
    '@type'
  ];
  switch (stateType) {
    case 'authorizationStateWaitTdlibParameters':
      return 'waitTdlibParameters';
    case 'authorizationStateWaitPhoneNumber':
      return 'waitPhoneNumber';
    case 'authorizationStateWaitCode':
      return 'waitCode';
    case 'authorizationStateWaitPassword':
      return 'waitPassword';
    case 'authorizationStateReady':
      return 'ready';
    case 'authorizationStateClosed':
      return 'closed';
    default:
      return 'unknown';
  }
}

/**
 * Handle TDLib updates (authorization state changes, etc.)
 */
function handleUpdate(update: TdUpdate): void {
  const s = globalThis.getTelegramSkillState();
  const updateType = update['@type'];

  // Enhanced logging for auth state debugging
  const isAuthUpdate = updateType === 'updateAuthorizationState';
  const isImportantUpdate =
    !updateType.startsWith('updateFile') &&
    !updateType.startsWith('updateOption') &&
    !updateType.startsWith('updateConnectionState');

  if (isAuthUpdate || isImportantUpdate) {
    const timestamp = new Date().toISOString().slice(11, -1); // HH:mm:ss.sss format
    console.log(`[telegram] ${timestamp} TDLib update:`, updateType);

    if (isAuthUpdate && (update as any).authorization_state) {
      console.log(
        `[telegram] ${timestamp} Full auth state object:`,
        JSON.stringify((update as any).authorization_state, null, 2)
      );
    }
  }

  // Dispatch to storage handlers for persistence
  globalThis.telegramDispatchUpdate(update);

  if (updateType === 'updateAuthorizationState') {
    const prevState = s.authState;
    const newState = parseAuthState(update);
    const timestamp = new Date().toISOString().slice(11, -1);

    // Detect unusual auth state transitions that might indicate problems
    const transitions = { from: prevState, to: newState, timestamp: Date.now() };

    // Log concerning patterns
    if (prevState === 'waitPhoneNumber' && newState === 'unknown') {
      console.warn(
        `[telegram] ${timestamp} CONCERNING: Auth regressed from waitPhoneNumber to unknown - possible database issue`
      );
    }

    if (prevState === 'waitCode' && newState === 'unknown') {
      console.warn(
        `[telegram] ${timestamp} CONCERNING: Auth regressed from waitCode to unknown - possible session corruption`
      );
    }

    // Count rapid state changes (potential indicator of instability)
    if (!(s as any)._authTransitionHistory) (s as any)._authTransitionHistory = [];
    (s as any)._authTransitionHistory.push(transitions);

    // Keep only last 10 transitions
    if ((s as any)._authTransitionHistory.length > 10) {
      (s as any)._authTransitionHistory.shift();
    }

    // Check for rapid transitions (5+ transitions in 5 seconds)
    const fiveSecondsAgo = Date.now() - 5000;
    const recentTransitions = (s as any)._authTransitionHistory.filter(
      (t: any) => t.timestamp > fiveSecondsAgo
    );
    if (recentTransitions.length >= 5) {
      console.warn(
        `[telegram] ${timestamp} WARNING: Rapid auth state changes detected (${recentTransitions.length} in 5s) - possible instability`
      );
      console.warn(
        '[telegram] Recent transitions:',
        recentTransitions.map((t: any) => `${t.from}->${t.to}`).join(', ')
      );
    }

    s.authState = newState;
    console.log(`[telegram] ${timestamp} Auth state changed: ${prevState} -> ${s.authState}`);
    console.log(
      `[telegram] ${timestamp} Race condition debug - auth state updated at: ${Date.now()}`
    );

    // Notify waiting functions of auth state change (event-based approach)
    try {
      console.log(
        `[telegram] ${timestamp} Triggering ${s.authStateChangeNotifier?.listeners?.length || 0} auth state listeners`
      );
      s.authStateChangeNotifier.notify(newState);
    } catch (e) {
      console.error('[telegram] Error notifying auth state listeners:', e);
    }

    // Extract password hint if waiting for password
    if (s.authState === 'waitPassword') {
      const authState = (update as { authorization_state?: { password_hint?: string } })
        .authorization_state;
      s.passwordHint = authState?.password_hint || null;
    }

    if (s.authState === 'waitTdlibParameters') {
      console.log('[telegram] Waiting for TDLib parameters');
      if (s.client) s.client.init(s.config.dataDir);
    }

    // Handle ready state
    if (s.authState === 'ready') {
      s.config.isAuthenticated = true;
      s.config.pendingCode = false;
      state.set('config', s.config);
      console.log(`[telegram] ${timestamp} User authenticated successfully`);
      loadMe();
    }

    // Force immediate state publication with critical state sync
    publishState();

    // For critical auth state changes, add explicit verification
    const criticalStates = ['waitCode', 'waitPassword', 'ready'];
    if (criticalStates.includes(newState)) {
      console.log(
        `[telegram] ${timestamp} CRITICAL STATE SYNC: Ensuring ${newState} propagates to frontend`
      );

      // Small delay to ensure state propagation, then re-publish
      setTimeout(() => {
        publishState();
        console.log(`[telegram] ${timestamp} Critical state re-published: ${newState}`);
      }, 25);
    }
  }
}

// ---------------------------------------------------------------------------
// Client Management
// ---------------------------------------------------------------------------

/**
 * Initialize the TDLib client and start the update loop.
 */
async function initClient(): Promise<void> {
  console.log('[telegram] initClient');
  const s = globalThis.getTelegramSkillState();

  // Check if client already exists or is being created
  if (s.client) {
    console.log('[telegram] Client already exists, skipping init');
    return;
  }
  if (s.clientConnecting) {
    console.log('[telegram] Client is already connecting, skipping init');
    return;
  }

  // Get TdLibClient class from globalThis
  const TdLibClientClass = getTdLibClientClass();

  // Check if TDLib is available
  if (!TdLibClientClass.isAvailable()) {
    console.warn('[telegram] TDLib is not available on this platform');
    s.clientError = 'TDLib is not available on this platform';
    publishState();
    return;
  }

  s.clientConnecting = true;
  s.clientError = null;
  publishState();

  try {
    // Create JS wrapper — TDLib itself is already running (Rust pre-initializes
    // the client + parameters at app startup, so no I/O needed here).
    const client = new TdLibClientClass();
    await client.init();

    // Store client in state
    s.client = client;

    console.log(
      '[telegram] Connected to TDLib, polling for auth state with states as...',
      s.authState
    );

    // Start the background update loop immediately for all TDLib communication
    // This eliminates race conditions between manual polling and background processing
    client.startUpdateLoop(handleUpdate);
    console.log('[telegram] Background update loop started, auth state:', s.authState);

    // Note: getAuthorizationState is not supported by V8 TDLib runtime
    // The background update loop will receive auth state updates automatically
    console.log('[telegram] Relying on background update loop for initial auth state');

    s.clientConnecting = false;
    publishState();
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    console.error('[telegram] Failed to initialize TDLib:', errorMsg);
    s.clientError = errorMsg;
    s.clientConnecting = false;
    s.client = null;
    publishState();
    throw err;
  }
}

/**
 * Load current user info after authentication.
 */
async function loadMe(): Promise<void> {
  const s = globalThis.getTelegramSkillState();
  if (!s.client) return;

  try {
    console.log('[telegram] Loading user info...');
    const me: TdUser = await s.client.getMe();
    if (me) {
      s.cache.me = {
        id: String(me.id),
        firstName: me.first_name,
        lastName: me.last_name,
        username: me.usernames?.active_usernames?.[0],
        phoneNumber: me.phone_number,
        isBot: false,
        isPremium: me.is_premium,
      };
      s.cache.lastSync = Date.now();
      console.log('[telegram] Loaded user:', s.cache.me.username || s.cache.me.firstName);
    }
    publishState();
  } catch (e) {
    console.error('[telegram] Failed to load me:', e);
  }
}

/**
 * Trigger initial sync of chats, messages, and contacts.
 * Can be called manually (re-sync) or automatically after authentication.
 */
async function onSync(): Promise<void> {
  const s = globalThis.getTelegramSkillState();

  // Skip if already syncing
  if (s.sync.inProgress) {
    console.log('[telegram] Initial sync already in progress');
    return;
  }

  // For manual re-sync: clear the completed flag so sync runs again
  if (globalThis.telegramSync.isSyncCompleted()) {
    console.log('[telegram] Clearing previous sync state for re-sync');
    globalThis.telegramDb.setSyncState('initial_sync_completed', '');
  }

  if (!s.client) {
    console.log('[telegram] Cannot sync: client not available');
    return;
  }

  s.sync.inProgress = true;
  s.sync.error = null;
  s.sync.progress = 0;
  s.sync.progressMessage = 'Starting sync...';
  publishState();

  try {
    await globalThis.telegramSync.performInitialSync(s.client, (msg, pct) => {
      s.sync.progress = pct;
      s.sync.progressMessage = msg;
      publishState();
    });

    s.sync.completed = true;
    s.sync.lastSyncTime = Date.now();
    s.sync.inProgress = false;
    s.sync.error = null;
    s.sync.progress = null;
    s.sync.progressMessage = null;

    updateStorageStats();
    console.log('[telegram] Initial sync completed successfully');
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    console.error('[telegram] Initial sync failed:', errorMsg);
    s.sync.inProgress = false;
    s.sync.error = errorMsg;
    s.sync.progress = null;
    s.sync.progressMessage = null;
  }

  publishState();
}

/**
 * Update storage statistics from database.
 */
function updateStorageStats(): void {
  const s = globalThis.getTelegramSkillState();
  try {
    const stats = globalThis.telegramDb.getStorageStats();
    s.storage = {
      chatCount: stats.chatCount,
      messageCount: stats.messageCount,
      contactCount: stats.contactCount,
      unreadCount: stats.unreadCount,
    };
  } catch (err) {
    console.error('[telegram] Failed to update storage stats:', err);
  }
}

// ---------------------------------------------------------------------------
// Lifecycle Hooks
// ---------------------------------------------------------------------------

async function init(): Promise<void> {
  console.log('[telegram] Initializing skill');

  // Get TdLibClient class from globalThis
  const TdLibClientClass = getTdLibClientClass();

  // Check runtime capabilities
  console.log(`[telegram] TDLib available: ${TdLibClientClass.isAvailable()}`);
  console.log(`[telegram] setTimeout available: ${typeof setTimeout !== 'undefined'}`);

  // Create database tables
  globalThis.initializeTelegramSchema();

  // Load config from store
  const s = globalThis.getTelegramSkillState();
  const saved = state.get('config') as Partial<typeof s.config> | null;
  if (saved) {
    s.config.phoneNumber = saved.phoneNumber || '';
    s.config.isAuthenticated = saved.isAuthenticated || false;
    s.config.dataDir = saved.dataDir || '';
    s.config.pendingCode = saved.pendingCode || false;
    s.config.showSensitiveMessages = saved.showSensitiveMessages ?? s.config.showSensitiveMessages;
  }

  console.log(`[telegram] Authenticated: ${s.config.isAuthenticated}`);

  // Load sync state from database
  s.sync.completed = globalThis.telegramSync.isSyncCompleted();
  s.sync.lastSyncTime = globalThis.telegramSync.getLastSyncTime();

  // Update storage stats if sync was completed
  if (s.sync.completed) {
    updateStorageStats();
  }

  // Initialize client
  initClient().catch(err => {
    console.error('[telegram] Failed to initialize client:', err);
    const errorMsg = err instanceof Error ? err.message : String(err);
    onError({ type: 'network', message: errorMsg, source: 'initClient', recoverable: true });
  });

  publishState();
}

async function start(): Promise<void> {
  console.log('[telegram] Starting skill');
  // The update loop is already running from initClient
}

async function stop(): Promise<void> {
  console.log('[telegram] Stopping skill');
  console.log('[telegram] Disconnecting skill and performing cleanup');
  const s = globalThis.getTelegramSkillState();

  try {
    // If authenticated, log out from Telegram servers first
    if (s.client && (s.authState === 'ready' || s.config.isAuthenticated)) {
      console.log('[telegram] Logging out from Telegram servers');
      await s.client.logOut().catch(e => {
        const errorMsg = e instanceof Error ? e.message : String(e);
        console.warn('[telegram] Error during logout:', errorMsg);
      });
    }

    // // Destroy TDLib client
    // if (s.client) {
    //   await s.client.destroy().catch(e => {
    //     const errorMsg = e instanceof Error ? e.message : String(e);
    //     console.warn('[telegram] Error destroying client:', errorMsg);
    //   });

    //   s.client = null;
    // }
  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : String(e);
    console.warn('[telegram] Error during disconnect:', errorMsg);
  }

  // Clear authentication state
  s.config.isAuthenticated = false;
  s.config.pendingCode = false;
  s.config.phoneNumber = '';
  s.authState = 'unknown';
  s.authOperationInProgress = false;
  s.cache.me = null;
  s.cache.lastSync = 0;
  s.passwordHint = null;
  s.clientError = null;
  s.clientConnecting = false;

  // Save cleared config
  state.set('config', s.config);
  state.set('status', 'stopped');

  // Publish updated state to frontend
  publishState();

  console.log('[telegram] Disconnect cleanup completed');
}

async function onCronTrigger(_scheduleId: string): Promise<void> {
  // No-op: TDLib update loop handles everything
}

async function onListOptions(): Promise<{ options: SkillOption[] }> {
  const s = globalThis.getTelegramSkillState();
  return {
    options: [
      {
        name: 'showSensitiveMessages',
        type: 'boolean',
        label: 'Show Sensitive Messages',
        value: s.config.showSensitiveMessages ?? false,
      },
      {
        name: 'allowGroupAdminActions',
        type: 'boolean',
        label: 'Allow Group Admin Actions',
        value: s.config.allowGroupAdminActions ?? false,
      },
      {
        name: 'allowWriteActions',
        type: 'boolean',
        label: 'Allow Write Actions',
        value: s.config.allowWriteActions ?? false,
      },
    ],
  };
}

async function onSetOption(args: { name: string; value: unknown }): Promise<void> {
  const s = globalThis.getTelegramSkillState();
  if (args.name === 'showSensitiveMessages') {
    s.config.showSensitiveMessages = Boolean(args.value);
    state.set('config', s.config);
  }
}

async function publishState(): Promise<void> {
  const s = globalThis.getTelegramSkillState();
  const isConnected = s.client !== null && s.client.initialized;
  const isConnecting = s.clientConnecting;
  const isAuthenticated = s.config.isAuthenticated;

  // Map to SkillHostConnectionState fields expected by the frontend
  const connection_status: string = s.clientError
    ? 'error'
    : isConnecting
      ? 'connecting'
      : isConnected
        ? 'connected'
        : 'disconnected';

  const auth_status: string = s.clientError
    ? 'error'
    : isAuthenticated
      ? 'authenticated'
      : s.authState === 'waitCode' || s.authState === 'waitPassword'
        ? 'authenticating'
        : 'not_authenticated';

  const timestamp = new Date().toISOString().slice(11, -1);
  const stateData = {
    // Standard SkillHostConnectionState fields
    connection_status,
    auth_status,
    connection_error: s.clientError || null,
    auth_error: null,
    is_initialized: isConnected,
    // Skill-specific fields
    authState: s.authState,
    pendingCode: s.config.pendingCode,
    phoneNumber: s.config.phoneNumber,
    me: s.cache.me,
    dialogCount: s.cache.dialogs.length,
    lastSync: s.cache.lastSync,
    error: s.clientError,
    // Sync state
    syncInProgress: s.sync.inProgress,
    syncCompleted: s.sync.completed,
    syncError: s.sync.error,
    lastSyncTime: s.sync.lastSyncTime,
    syncProgress: s.sync.progress,
    syncProgressMessage: s.sync.progressMessage,
    // Storage statistics
    storage: {
      chatCount: s.storage.chatCount,
      messageCount: s.storage.messageCount,
      contactCount: s.storage.contactCount,
      unreadCount: s.storage.unreadCount,
    },
  };

  // Log critical state changes for debugging frontend sync issues
  const criticalStateChanges = [
    s.authState === 'waitCode' && 'AUTH_STATE_WAIT_CODE',
    s.authState === 'waitPassword' && 'AUTH_STATE_WAIT_PASSWORD',
    s.authState === 'ready' && 'AUTH_STATE_READY',
    s.config.isAuthenticated && 'IS_AUTHENTICATED',
    s.clientError && 'CLIENT_ERROR',
  ].filter(Boolean);

  if (criticalStateChanges.length > 0) {
    console.log(
      `[telegram] ${timestamp} PUBLISHING CRITICAL STATE: ${criticalStateChanges.join(', ')}`
    );
    console.log(
      `[telegram] ${timestamp} Frontend state sync - authState: ${s.authState}, auth_status: ${auth_status}, isAuthenticated: ${isAuthenticated}`
    );
  }

  // Publish state with verification
  try {
    state.setPartial(stateData);

    // Verify the state was set by checking a sample field
    const testKey = 'authState';
    const publishedValue = state.get(testKey);
    if (publishedValue !== s.authState) {
      console.warn(
        `[telegram] ${timestamp} STATE SYNC WARNING: Published ${testKey}=${publishedValue} but expected ${s.authState}`
      );
    } else if (criticalStateChanges.length > 0) {
      console.log(
        `[telegram] ${timestamp} State sync verification passed - ${testKey} correctly published as ${publishedValue}`
      );
    }
  } catch (e) {
    console.error(`[telegram] ${timestamp} FAILED TO PUBLISH STATE:`, e);
  }
}

// ---------------------------------------------------------------------------
// Exports to globalThis (required for V8 runtime)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Tool Definitions
// ---------------------------------------------------------------------------

/**
 * telegram-status tool - Get current connection status.
 */
const telegramStatusTool: ToolDefinition = {
  name: 'telegram-status',
  description: 'Get current Telegram connection and authentication status.',
  input_schema: { type: 'object', properties: {}, required: [] },
  async execute(): Promise<string> {
    const s = globalThis.getTelegramSkillState();
    return JSON.stringify({
      connected: s.client !== null && s.client.initialized,
      connecting: s.clientConnecting,
      authenticated: s.config.isAuthenticated,
      authState: s.authState,
      phoneNumber: s.config.phoneNumber ? s.config.phoneNumber.slice(0, 4) + '****' : null,
      me: s.cache.me,
      syncInProgress: s.sync.inProgress,
      syncCompleted: s.sync.completed,
      lastSyncTime: s.sync.lastSyncTime,
      storage: s.storage,
      error: s.clientError || s.sync.error,
    });
  },
};

// ---------------------------------------------------------------------------
// Skill Export
// ---------------------------------------------------------------------------

async function onPing(): Promise<PingResult> {
  console.log('[telegram] onPing');
  const s = globalThis.getTelegramSkillState();
  if (!s.client || !s.client.initialized) {
    console.log('[telegram] onPing: TDLib client not connected');
    return { ok: false, errorType: 'network', errorMessage: 'TDLib client not connected' };
  }
  if (!s.config.isAuthenticated || s.authState !== 'ready') {
    console.log(`[telegram] onPing: Not authenticated (state: ${s.authState})`);
    return {
      ok: false,
      errorType: 'auth',
      errorMessage: `Not authenticated (state: ${s.authState})`,
    };
  }

  console.log('[telegram] onPing: Getting me');
  const me = await getMe(s.client);
  console.log('[telegram] onPing:', JSON.stringify(me));

  return { ok: true };
}

async function onError(args: SkillErrorArgs): Promise<void> {
  const s = globalThis.getTelegramSkillState();
  console.error(
    `[telegram] onError: type=${args.type} source=${args.source || 'unknown'} message=${args.message}`
  );

  s.clientError = args.message;

  // For auth errors during login, reset the pending code flag and clear auth operation mutex
  if (args.type === 'auth' || args.source === 'setAuthenticationPhoneNumber') {
    s.config.pendingCode = false;
    s.authOperationInProgress = false;
    state.set('config', s.config);
  }

  publishState();
}

const { onSetupStart, onSetupSubmit, onSetupCancel } = createSetupHandlers({
  initClient,
  onError,
  publishState,
});

const skill: Skill = {
  info: {
    id: 'telegram',
    name: 'Telegram',
    version: '2.1.0', // Bumped for persistent storage
    description: 'Telegram integration via TDLib with persistent storage',
    auto_start: false,
    setup: { required: true, label: 'Configure Telegram' },
  },
  tools: [telegramStatusTool, ...tools],
  init,
  start,
  stop,
  onCronTrigger,
  onSetupStart,
  onSetupSubmit,
  onSetupCancel,
  onPing,
  onError,
  onSync,
  onListOptions,
  onSetOption,
};

export default skill;
