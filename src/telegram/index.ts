// telegram/index.ts
// Telegram integration skill using TDLib via V8 runtime.
// Provides tools for Telegram API access with native TDLib bindings.

// Import skill state (initializes globalThis.getTelegramSkillState)
import './skill-state';
import type { SetupSubmitArgs, AuthorizationState } from './skill-state';

// Import TDLib client wrapper - this also assigns TdLibClient to globalThis
import './tdlib-client';
import type { TdUpdate, TdUser } from './tdlib-client';
// Import the class type for type assertions
import type { TdLibClient as TdLibClientType } from './tdlib-client';

// Import modules to register globalThis functions
import './db-schema'; // registers globalThis.initializeTelegramSchema
import './db-helpers'; // registers globalThis.telegramDb
import './update-handlers'; // registers globalThis.telegramDispatchUpdate
import './sync'; // registers globalThis.telegramSync

// Import tool definitions
import { getChatsToolDefinition } from './tools/get-chats';
import { getMessagesToolDefinition } from './tools/get-messages';
import { getContactsToolDefinition } from './tools/get-contacts';
import { getChatStatsToolDefinition } from './tools/get-chat-stats';

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

  // Log non-frequent updates
  if (!updateType.startsWith('updateFile') && !updateType.startsWith('updateOption')) {
    console.log('[telegram] TDLib update:', updateType);
  }

  // Dispatch to storage handlers for persistence
  globalThis.telegramDispatchUpdate(update);

  if (updateType === 'updateAuthorizationState') {
    const prevState = s.authState;
    s.authState = parseAuthState(update);
    console.log(`[telegram] Auth state changed: ${prevState} -> ${s.authState}`);

    // Extract password hint if waiting for password
    if (s.authState === 'waitPassword') {
      const authState = (update as { authorization_state?: { password_hint?: string } })
        .authorization_state;
      s.passwordHint = authState?.password_hint || null;
    }

    // Handle ready state
    if (s.authState === 'ready') {
      s.config.isAuthenticated = true;
      s.config.pendingCode = false;
      store.set('config', s.config);
      console.log('[telegram] User authenticated successfully');
      loadMe();

      // Trigger initial sync if not already completed
      triggerInitialSync();
    }

    publishState();
  }
}

// ---------------------------------------------------------------------------
// Client Management
// ---------------------------------------------------------------------------

/**
 * Initialize the TDLib client and start the update loop.
 */
async function initClient(): Promise<void> {
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

  // Need API credentials to initialize
  if (!s.config.apiId || !s.config.apiHash) {
    console.log('[telegram] No API credentials configured, skipping client init');
    return;
  }

  s.clientConnecting = true;
  s.clientError = null;
  publishState();

  console.log('[telegram] Creating TDLib client with apiId:', s.config.apiId);

  try {
    // Create TDLib client
    const client = new TdLibClientClass();

    // Determine data directory (use skill data directory)
    const dataDir = s.config.dataDir || getDefaultDataDir();
    s.config.dataDir = dataDir;

    console.log('[telegram] Initializing TDLib with data dir:', dataDir);
    await client.init(dataDir);

    // Store client in state
    s.client = client;

    // Start update loop
    client.startUpdateLoop(handleUpdate);

    // Set TDLib parameters (this triggers the auth flow)
    console.log('[telegram] Setting TDLib parameters...');
    await client.setTdlibParameters({
      api_id: s.config.apiId,
      api_hash: s.config.apiHash,
      database_directory: dataDir,
      files_directory: dataDir + '/files',
      use_message_database: true,
      use_secret_chats: false,
      system_language_code: 'en',
      device_model: 'Desktop',
      application_version: '1.0.0',
    });

    console.log('[telegram] TDLib parameters set, waiting for auth state...');

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
 * Get default data directory for TDLib files.
 */
function getDefaultDataDir(): string {
  // Use the skill's data directory if available via platform
  // Otherwise use a reasonable default
  const os = platform.os();
  if (os === 'windows') {
    return 'C:/Users/Public/AlphaHuman/telegram';
  } else if (os === 'macos') {
    return '/tmp/alphahuman/telegram';
  } else {
    return '/tmp/alphahuman/telegram';
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
 */
async function triggerInitialSync(): Promise<void> {
  const s = globalThis.getTelegramSkillState();

  // Skip if already syncing or completed
  if (s.sync.inProgress) {
    console.log('[telegram] Initial sync already in progress');
    return;
  }

  // Check if sync was already completed
  if (globalThis.telegramSync.isSyncCompleted()) {
    console.log('[telegram] Initial sync already completed');
    s.sync.completed = true;
    s.sync.lastSyncTime = globalThis.telegramSync.getLastSyncTime();
    updateStorageStats();
    publishState();
    return;
  }

  if (!s.client) {
    console.log('[telegram] Cannot sync: client not available');
    return;
  }

  s.sync.inProgress = true;
  s.sync.error = null;
  publishState();

  try {
    await globalThis.telegramSync.performInitialSync(s.client, (msg) => {
      console.log(`[telegram-sync] ${msg}`);
    });

    s.sync.completed = true;
    s.sync.lastSyncTime = Date.now();
    s.sync.inProgress = false;
    s.sync.error = null;

    updateStorageStats();
    console.log('[telegram] Initial sync completed successfully');
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    console.error('[telegram] Initial sync failed:', errorMsg);
    s.sync.inProgress = false;
    s.sync.error = errorMsg;
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

/**
 * Send phone number for authentication.
 */
async function sendPhoneNumber(phoneNumber: string): Promise<void> {
  const s = globalThis.getTelegramSkillState();
  if (!s.client) {
    throw new Error('TDLib client not initialized');
  }

  console.log('[telegram] Sending phone number for auth...');
  s.config.phoneNumber = phoneNumber;
  s.config.pendingCode = true;
  store.set('config', s.config);

  await s.client.setAuthenticationPhoneNumber(phoneNumber);
  console.log('[telegram] Phone number sent, waiting for code...');
  publishState();
}

/**
 * Submit verification code.
 */
async function submitCode(code: string): Promise<void> {
  const s = globalThis.getTelegramSkillState();
  if (!s.client) {
    throw new Error('TDLib client not initialized');
  }

  console.log('[telegram] Submitting verification code...');
  await s.client.checkAuthenticationCode(code);
  console.log('[telegram] Code submitted');
}

/**
 * Submit 2FA password.
 */
async function submitPassword(password: string): Promise<void> {
  const s = globalThis.getTelegramSkillState();
  if (!s.client) {
    throw new Error('TDLib client not initialized');
  }

  console.log('[telegram] Submitting 2FA password...');
  await s.client.checkAuthenticationPassword(password);
  console.log('[telegram] Password submitted');
}

// ---------------------------------------------------------------------------
// Lifecycle Hooks
// ---------------------------------------------------------------------------

function init(): void {
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
  const saved = store.get('config') as Partial<typeof s.config> | null;
  if (saved) {
    s.config.apiId = saved.apiId || 0;
    s.config.apiHash = saved.apiHash || '';
    s.config.phoneNumber = saved.phoneNumber || '';
    s.config.isAuthenticated = saved.isAuthenticated || false;
    s.config.dataDir = saved.dataDir || '';
    s.config.pendingCode = saved.pendingCode || false;
  }

  // Load from environment if not in store
  if (!s.config.apiId) {
    const envApiId = platform.env('TELEGRAM_API_ID');
    if (envApiId) {
      s.config.apiId = parseInt(envApiId, 10);
    }
  }
  if (!s.config.apiHash) {
    s.config.apiHash = platform.env('TELEGRAM_API_HASH') || '';
  }

  console.log(
    `[telegram] Config loaded — apiId: ${s.config.apiId ? 'set' : 'not set'}, apiHash: ${s.config.apiHash ? 'set' : 'not set'}`
  );
  console.log(`[telegram] Authenticated: ${s.config.isAuthenticated}`);

  // Load sync state from database
  s.sync.completed = globalThis.telegramSync.isSyncCompleted();
  s.sync.lastSyncTime = globalThis.telegramSync.getLastSyncTime();

  // Update storage stats if sync was completed
  if (s.sync.completed) {
    updateStorageStats();
  }

  // Initialize client if we have credentials
  if (s.config.apiId && s.config.apiHash) {
    initClient().catch((err) => {
      console.error('[telegram] Init client failed:', err);
    });
  }

  publishState();
}

function start(): void {
  console.log('[telegram] Starting skill');
  // The update loop is already running from initClient
}

function stop(): void {
  console.log('[telegram] Stopping skill');
  const s = globalThis.getTelegramSkillState();

  // Destroy TDLib client
  if (s.client) {
    try {
      s.client.destroy().catch((e) => {
        console.warn('[telegram] Error destroying client:', e);
      });
    } catch (e) {
      console.warn('[telegram] Error destroying client:', e);
    }
    s.client = null;
  }

  // Save config
  store.set('config', s.config);
  state.set('status', 'stopped');
}

function onCronTrigger(_scheduleId: string): void {
  // No-op: TDLib update loop handles everything
}

// ---------------------------------------------------------------------------
// Setup Flow
// ---------------------------------------------------------------------------

function onSetupStart(): SetupStartResult {
  const envApiId = platform.env('TELEGRAM_API_ID');
  const envApiHash = platform.env('TELEGRAM_API_HASH');
  console.log(`[telegram] onSetupStart: envApiId: ${envApiId ? 'set' : 'not set'}`);

  // If API credentials are in environment, skip to phone step
  if (envApiId && envApiHash) {
    const s = globalThis.getTelegramSkillState();
    s.config.apiId = parseInt(envApiId, 10);
    s.config.apiHash = envApiHash;
    store.set('config', s.config);

    // Start client initialization in background
    if (!s.client && !s.clientConnecting) {
      initClient().catch((err) => {
        console.error('[telegram] Init client failed:', err);
      });
    }

    return {
      step: {
        id: 'phone',
        title: 'Connect Telegram Account',
        description: 'Enter your phone number to connect your Telegram account.',
        fields: [
          {
            name: 'phoneNumber',
            type: 'text',
            label: 'Phone Number',
            description: 'International format (e.g., +1234567890)',
            required: true,
            placeholder: '+1234567890',
          },
        ],
      },
    };
  }

  return {
    step: {
      id: 'credentials',
      title: 'Telegram API Credentials',
      description:
        'Enter your Telegram API credentials from my.telegram.org. ' +
        'Then you will enter your phone number.',
      fields: [
        {
          name: 'apiId',
          type: 'text',
          label: 'API ID',
          description: 'Your Telegram API ID (numeric)',
          required: true,
          placeholder: '12345678',
        },
        {
          name: 'apiHash',
          type: 'password',
          label: 'API Hash',
          description: 'Your Telegram API Hash',
          required: true,
          placeholder: 'abc123...',
        },
      ],
    },
  };
}

function onSetupSubmit(args: SetupSubmitArgs): SetupSubmitResult {
  const s = globalThis.getTelegramSkillState();
  const { stepId, values } = args;

  if (stepId === 'credentials') {
    const apiId = parseInt((values.apiId as string) || '', 10);
    const apiHash = ((values.apiHash as string) || '').trim();

    console.log(
      `[telegram] Setup: credentials step - apiId: ${apiId}, apiHash: ${apiHash ? '[set]' : '[empty]'}`
    );

    if (!apiId || isNaN(apiId)) {
      return { status: 'error', errors: [{ field: 'apiId', message: 'Valid API ID is required' }] };
    }
    if (!apiHash) {
      return { status: 'error', errors: [{ field: 'apiHash', message: 'API Hash is required' }] };
    }

    s.config.apiId = apiId;
    s.config.apiHash = apiHash;
    store.set('config', s.config);

    // Start client initialization in background
    initClient().catch((err) => {
      console.error('[telegram] Init client failed:', err);
    });

    return {
      status: 'next',
      nextStep: {
        id: 'phone',
        title: 'Connect Telegram Account',
        description:
          'Enter your phone number to connect your Telegram account. Please wait a moment for the connection to establish.',
        fields: [
          {
            name: 'phoneNumber',
            type: 'text',
            label: 'Phone Number',
            description: 'International format (e.g., +1234567890)',
            required: true,
            placeholder: '+1234567890',
          },
        ],
      },
    };
  }

  if (stepId === 'phone') {
    const phoneNumber = ((values.phoneNumber as string) || '').trim();

    console.log(
      `[telegram] Setup: phone step - number: ${phoneNumber ? phoneNumber.slice(0, 4) + '****' : '[empty]'}`
    );
    console.log(
      `[telegram] Setup: client connected: ${s.client !== null}, connecting: ${s.clientConnecting}, authState: ${s.authState}`
    );

    if (!phoneNumber || !phoneNumber.startsWith('+')) {
      return {
        status: 'error',
        errors: [
          {
            field: 'phoneNumber',
            message: 'Phone number must start with + (international format)',
          },
        ],
      };
    }

    // Check if client is ready
    if (!s.client) {
      if (s.clientConnecting) {
        return {
          status: 'error',
          errors: [
            {
              field: 'phoneNumber',
              message: 'Still connecting to Telegram. Please wait a moment and try again.',
            },
          ],
        };
      }
      return {
        status: 'error',
        errors: [
          {
            field: 'phoneNumber',
            message: 'Client not connected. Please restart setup.',
          },
        ],
      };
    }

    // Check auth state - should be waiting for phone number
    if (s.authState !== 'waitPhoneNumber' && s.authState !== 'unknown') {
      console.log(`[telegram] Unexpected auth state for phone step: ${s.authState}`);
    }

    // Send phone number (async - errors will be caught by update handler)
    sendPhoneNumber(phoneNumber).catch((err) => {
      console.error('[telegram] Failed to send phone number:', err);
      s.clientError = err instanceof Error ? err.message : String(err);
      publishState();
    });

    return {
      status: 'next',
      nextStep: {
        id: 'code',
        title: 'Enter Verification Code',
        description:
          'A verification code has been sent to your Telegram app or SMS. Enter it below.',
        fields: [
          {
            name: 'code',
            type: 'text',
            label: 'Verification Code',
            description: '5-digit code from Telegram',
            required: true,
            placeholder: '12345',
          },
        ],
      },
    };
  }

  if (stepId === 'code') {
    const code = ((values.code as string) || '').trim();

    console.log(`[telegram] Setup: code step - authState: ${s.authState}`);

    if (!code) {
      return {
        status: 'error',
        errors: [{ field: 'code', message: 'Verification code is required' }],
      };
    }

    // Submit code (async)
    submitCode(code).catch((err) => {
      console.error('[telegram] Failed to submit code:', err);
      s.clientError = err instanceof Error ? err.message : String(err);
      publishState();
    });

    // Check if we need 2FA password
    // Give TDLib a moment to process
    // In practice, the update handler will set authState
    if (s.authState === 'waitPassword') {
      return {
        status: 'next',
        nextStep: {
          id: 'password',
          title: 'Two-Factor Authentication',
          description: s.passwordHint
            ? `Enter your 2FA password. Hint: ${s.passwordHint}`
            : 'Enter your 2FA password.',
          fields: [
            {
              name: 'password',
              type: 'password',
              label: '2FA Password',
              description: 'Your Telegram 2FA password',
              required: true,
            },
          ],
        },
      };
    }

    // If already authenticated or will be soon, complete setup
    return { status: 'complete' };
  }

  if (stepId === 'password') {
    const password = ((values.password as string) || '').trim();

    console.log('[telegram] Setup: password step');

    if (!password) {
      return {
        status: 'error',
        errors: [{ field: 'password', message: '2FA password is required' }],
      };
    }

    // Submit password (async)
    submitPassword(password).catch((err) => {
      console.error('[telegram] Failed to submit password:', err);
      s.clientError = err instanceof Error ? err.message : String(err);
      publishState();
    });

    return { status: 'complete' };
  }

  return { status: 'error', errors: [{ field: '', message: `Unknown setup step: ${stepId}` }] };
}

function onSetupCancel(): void {
  console.log('[telegram] Setup cancelled');
  const s = globalThis.getTelegramSkillState();
  s.config.pendingCode = false;
  store.set('config', s.config);
}

function publishState(): void {
  const s = globalThis.getTelegramSkillState();
  state.setPartial({
    connected: s.client !== null && s.client.initialized,
    connecting: s.clientConnecting,
    authenticated: s.config.isAuthenticated,
    authState: s.authState,
    pendingCode: s.config.pendingCode,
    phoneNumber: s.config.phoneNumber ? s.config.phoneNumber.slice(0, 4) + '****' : null,
    hasCredentials: !!(s.config.apiId && s.config.apiHash),
    me: s.cache.me,
    dialogCount: s.cache.dialogs.length,
    lastSync: s.cache.lastSync,
    error: s.clientError,
    // Sync state
    syncInProgress: s.sync.inProgress,
    syncCompleted: s.sync.completed,
    syncError: s.sync.error,
    lastSyncTime: s.sync.lastSyncTime,
    // Storage statistics
    storage: {
      chatCount: s.storage.chatCount,
      messageCount: s.storage.messageCount,
      contactCount: s.storage.contactCount,
      unreadCount: s.storage.unreadCount,
    },
  });
}

// ---------------------------------------------------------------------------
// Exports to globalThis (required for V8 runtime)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Tool Definitions
// ---------------------------------------------------------------------------

/**
 * telegram-ping tool - Check Telegram connectivity.
 */
const telegramPingTool: ToolDefinition = {
  name: 'telegram-ping',
  description: 'Check if Telegram servers are reachable and get latency information.',
  input_schema: {
    type: 'object',
    properties: {},
    required: [],
  },
  execute(): string {
    const s = globalThis.getTelegramSkillState();
    const endpoints = [
      'https://telegram.org',
      'https://api.telegram.org',
      'https://core.telegram.org',
    ];

    const results: Array<{
      endpoint: string;
      success: boolean;
      latency_ms: number | null;
      error?: string;
    }> = [];

    for (const endpoint of endpoints) {
      const startTime = Date.now();
      try {
        const response = net.fetch(endpoint, { method: 'HEAD', timeout: 5000 });
        const latency = Date.now() - startTime;
        results.push({
          endpoint,
          success: response.status >= 200 && response.status < 300,
          latency_ms: latency,
        });
      } catch (err) {
        results.push({
          endpoint,
          success: false,
          latency_ms: null,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }

    const successCount = results.filter((r) => r.success).length;
    const avgLatency =
      successCount > 0
        ? Math.round(
            results
              .filter((r) => r.success && r.latency_ms !== null)
              .reduce((sum, r) => sum + (r.latency_ms || 0), 0) / successCount
          )
        : null;

    return JSON.stringify({
      success: successCount > 0,
      message:
        successCount > 0
          ? `Telegram is reachable (${successCount}/${endpoints.length} endpoints)`
          : 'Unable to reach Telegram servers',
      avg_latency_ms: avgLatency,
      has_credentials: !!(s.config.apiId && s.config.apiHash),
      is_authenticated: s.config.isAuthenticated,
      endpoints: results,
    });
  },
};

/**
 * telegram-status tool - Get current connection status.
 */
const telegramStatusTool: ToolDefinition = {
  name: 'telegram-status',
  description: 'Get current Telegram connection and authentication status.',
  input_schema: {
    type: 'object',
    properties: {},
    required: [],
  },
  execute(): string {
    const s = globalThis.getTelegramSkillState();
    return JSON.stringify({
      connected: s.client !== null && s.client.initialized,
      connecting: s.clientConnecting,
      authenticated: s.config.isAuthenticated,
      authState: s.authState,
      hasCredentials: !!(s.config.apiId && s.config.apiHash),
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

/**
 * telegram-sync tool - Trigger data synchronization.
 */
const telegramSyncTool: ToolDefinition = {
  name: 'telegram-sync',
  description: 'Trigger synchronization of Telegram data (chats, messages, contacts) to local storage.',
  input_schema: {
    type: 'object',
    properties: {
      force: {
        type: 'string',
        description: 'Force re-sync even if already completed (true/false)',
        enum: ['true', 'false'],
      },
    },
    required: [],
  },
  execute(args: Record<string, unknown>): string {
    const s = globalThis.getTelegramSkillState();
    const force = args.force === 'true';

    if (!s.config.isAuthenticated) {
      return JSON.stringify({
        success: false,
        error: 'Not authenticated. Please complete Telegram setup first.',
      });
    }

    if (s.sync.inProgress) {
      return JSON.stringify({
        success: false,
        error: 'Sync already in progress.',
        syncInProgress: true,
      });
    }

    if (s.sync.completed && !force) {
      return JSON.stringify({
        success: true,
        message: 'Sync already completed. Use force=true to re-sync.',
        lastSyncTime: s.sync.lastSyncTime,
        storage: s.storage,
      });
    }

    // Trigger sync in background
    triggerInitialSync().catch((err) => {
      console.error('[telegram] Sync trigger failed:', err);
    });

    return JSON.stringify({
      success: true,
      message: 'Sync started. Check status with telegram-status tool.',
      syncInProgress: true,
    });
  },
};

// ---------------------------------------------------------------------------
// Skill Export
// ---------------------------------------------------------------------------

const skill: Skill = {
  info: {
    id: 'telegram',
    name: 'Telegram',
    runtime: 'v8',
    entry: 'index.js',
    version: '2.1.0', // Bumped for persistent storage
    description: 'Telegram integration via TDLib with persistent storage',
    auto_start: false,
    setup: { required: true, label: 'Configure Telegram' },
  },
  tools: [
    telegramPingTool,
    telegramStatusTool,
    telegramSyncTool,
    getChatsToolDefinition,
    getMessagesToolDefinition,
    getContactsToolDefinition,
    getChatStatsToolDefinition,
  ],
  init,
  start,
  stop,
  onCronTrigger,
  onSetupStart,
  onSetupSubmit,
  onSetupCancel,
};

export default skill;
