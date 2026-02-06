/**
 * example-skill — Kitchen-sink skill demonstrating every bridge API,
 * lifecycle hook, setup wizard, options system, and tool pattern.
 *
 * Use this as a reference when building your own skill.
 */
// ─── State & Types ───────────────────────────────────────────────────
import { getState } from './skill-state';
import { DEFAULT_CONFIG, type ExampleConfig } from './types';

// ─── Tools ───────────────────────────────────────────────────────────
// Tools are exposed to the AI and other skills.
// Each tool.execute() must return a JSON string.
// NOTE: Tools are defined inline to avoid cross-module bundling issues.

tools = [
  // get-status — returns current skill status, config summary, and error count
  {
    name: 'get-status',
    description: 'Get current skill status including configuration summary and error count.',
    input_schema: {
      type: 'object',
      properties: {
        verbose: {
          type: 'string',
          enum: ['true', 'false'],
          description: 'Include full config in response (default: false)',
        },
      },
    },
    execute(args: Record<string, unknown>): string {
      const s = getState();
      const verbose = args.verbose === 'true';

      const result: Record<string, unknown> = {
        status: s.isRunning ? 'running' : 'stopped',
        fetchCount: s.fetchCount,
        errorCount: s.errorCount,
        lastFetchTime: s.lastFetchTime,
        refreshInterval: s.config.refreshInterval,
        platform: platform.os(),
      };

      if (verbose)
        result.config = {
          serverUrl: s.config.serverUrl,
          refreshInterval: s.config.refreshInterval,
          notifyOnError: s.config.notifyOnError,
          verbose: s.config.verbose,
        };

      return JSON.stringify(result);
    },
  },

  // fetch-data — makes an HTTP request to the configured server URL
  {
    name: 'fetch-data',
    description: 'Fetch data from the configured server URL. Returns the response status and body.',
    input_schema: {
      type: 'object',
      properties: {
        endpoint: {
          type: 'string',
          description: 'Optional path to append to the server URL (e.g., "/health")',
        },
      },
    },
    execute(args: Record<string, unknown>): string {
      const s = getState();
      const endpoint = (args.endpoint as string) || '';
      const url = s.config.serverUrl + endpoint;

      if (!s.config.serverUrl) return JSON.stringify({ error: 'Server URL not configured' });

      try {
        const response = net.fetch(url, {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${s.config.apiKey}`,
            'Content-Type': 'application/json',
          },
          timeout: 10000,
        });

        s.fetchCount++;
        s.lastFetchTime = new Date().toISOString();

        return JSON.stringify({ status: response.status, body: response.body });
      } catch (e) {
        s.errorCount++;
        return JSON.stringify({ error: String(e) });
      }
    },
  },

  // query-logs — query the SQLite logs table with limit
  {
    name: 'query-logs',
    description: 'Query recent log entries from the skill database.',
    input_schema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Maximum number of rows to return (default: 10)',
          minimum: 1,
          maximum: 100,
        },
      },
    },
    execute(args: Record<string, unknown>): string {
      const limit = typeof args.limit === 'number' ? args.limit : 10;
      const rows = db.all(`SELECT * FROM logs ORDER BY id DESC LIMIT ${limit}`, []);
      return JSON.stringify({ count: rows.length, rows });
    },
  },

  // list-peers — discover other skills via skills.list()
  {
    name: 'list-peers',
    description: 'List all registered skills in the runtime.',
    input_schema: { type: 'object', properties: {} },
    execute(_args: Record<string, unknown>): string {
      const peers = skills.list();
      return JSON.stringify({ count: peers.length, skills: peers });
    },
  },
];

// ─── Lifecycle: init() ──────────────────────────────────────────────
// Called once when the skill is first loaded.
// Use this to create database tables and load persisted config.
function init(): void {
  const s = getState();

  // Create database table for logs
  db.exec(
    `CREATE TABLE IF NOT EXISTS logs (
      id INTEGER PRIMARY KEY,
      level TEXT NOT NULL,
      message TEXT NOT NULL,
      created_at TEXT NOT NULL
    )`,
    []
  );

  // Load persisted configuration from store
  const saved = store.get('config') as Partial<ExampleConfig> | null;
  if (saved) {
    s.config = { ...DEFAULT_CONFIG, ...saved };
  }

  // Log initialization
  if (s.config.verbose)
    console.log('[example-skill] Initialized with config:', JSON.stringify(s.config));
}

// ─── Lifecycle: start() ─────────────────────────────────────────────
// Called when the skill should begin active work.
// Register cron schedules and publish initial state.
function start(): void {
  const s = getState();
  s.isRunning = true;

  // Register a cron schedule for periodic data fetching
  // 6-field syntax: seconds minutes hours day month dow
  cron.register('refresh', `*/${s.config.refreshInterval} * * * * *`);

  // Publish initial state to the frontend
  publishState();

  if (s.config.verbose)
    console.log('[example-skill] Started with interval:', s.config.refreshInterval);
}

// ─── Lifecycle: stop() ──────────────────────────────────────────────
// Called on shutdown. Unregister cron schedules and persist state.
function stop(): void {
  const s = getState();
  s.isRunning = false;

  // Unregister all cron schedules
  cron.unregister('refresh');

  // Persist configuration
  store.set('config', s.config);

  // Persist a data file with last-known state
  data.write(
    'last-state.json',
    JSON.stringify({
      fetchCount: s.fetchCount,
      errorCount: s.errorCount,
      lastFetchTime: s.lastFetchTime,
      stoppedAt: new Date().toISOString(),
    })
  );

  if (s.config.verbose) console.log('[example-skill] Stopped');
}

// ─── Lifecycle: onCronTrigger ───────────────────────────────────────
// Called when a registered cron schedule fires.
function onCronTrigger(scheduleId: string): void {
  if (scheduleId !== 'refresh') return;

  const s = getState();
  if (!s.config.serverUrl) return;

  try {
    const response = net.fetch(s.config.serverUrl, {
      method: 'GET',
      headers: { Authorization: `Bearer ${s.config.apiKey}`, 'Content-Type': 'application/json' },
      timeout: 10000,
    });

    s.fetchCount++;
    s.lastFetchTime = new Date().toISOString();

    // Log to database
    db.exec('INSERT INTO logs (level, message, created_at) VALUES (?, ?, ?)', [
      'info',
      `Fetch OK: status=${response.status}`,
      s.lastFetchTime,
    ]);

    // Reset error count on success
    s.errorCount = 0;
  } catch (e) {
    s.errorCount++;

    db.exec('INSERT INTO logs (level, message, created_at) VALUES (?, ?, ?)', [
      'error',
      `Fetch failed: ${String(e)}`,
      new Date().toISOString(),
    ]);

    // Send notification if configured
    if (s.config.notifyOnError)
      platform.notify('Example Skill Error', `Fetch failed: ${String(e)}`);
  }

  // Always publish updated state
  publishState();
}

// ─── Lifecycle: onSessionStart / onSessionEnd ───────────────────────
// Called when the user starts or ends an AI conversation.
function onSessionStart(_args: { sessionId: string }): void {
  const s = getState();
  if (s.config.verbose) console.log('[example-skill] Session started');
}

function onSessionEnd(_args: { sessionId: string }): void {
  const s = getState();
  if (s.config.verbose) console.log('[example-skill] Session ended');
}

// ─── Setup Flow (3-step wizard) ─────────────────────────────────────
// Multi-step configuration wizard presented to the user on first run.

function onSetupStart(): SetupStartResult {
  return {
    step: {
      id: 'credentials',
      title: 'API Credentials',
      description: 'Enter the server URL and API key.',
      fields: [
        {
          name: 'serverUrl',
          type: 'text',
          label: 'Server URL',
          description: 'Full URL (e.g., https://api.example.com)',
          required: true,
          placeholder: 'https://api.example.com',
        },
        {
          name: 'apiKey',
          type: 'password',
          label: 'API Key',
          description: 'Your API key for authentication',
          required: true,
        },
      ],
    },
  };
}

function onSetupSubmit(args: {
  stepId: string;
  values: Record<string, unknown>;
}): SetupSubmitResult {
  const s = getState();

  // Step 1: Credentials
  if (args.stepId === 'credentials') {
    const serverUrl = args.values.serverUrl as string;
    const apiKey = args.values.apiKey as string;

    if (!serverUrl)
      return {
        status: 'error',
        errors: [{ field: 'serverUrl', message: 'Server URL is required' }],
      };
    if (!apiKey)
      return { status: 'error', errors: [{ field: 'apiKey', message: 'API key is required' }] };

    s.config.serverUrl = serverUrl;
    s.config.apiKey = apiKey;

    // Advance to step 2
    return {
      status: 'next',
      nextStep: {
        id: 'webhook',
        title: 'Webhook Configuration',
        description: 'Optionally configure a webhook for external notifications.',
        fields: [
          {
            name: 'webhookUrl',
            type: 'text',
            label: 'Webhook URL',
            description: 'POST notifications to this URL (leave empty to skip)',
          },
        ],
      },
    };
  }

  // Step 2: Webhook
  if (args.stepId === 'webhook') {
    s.config.webhookUrl = (args.values.webhookUrl as string) || '';

    // Advance to step 3
    return {
      status: 'next',
      nextStep: {
        id: 'preferences',
        title: 'Notification Preferences',
        description: 'Choose your notification settings.',
        fields: [
          {
            name: 'notifyOnError',
            type: 'boolean',
            label: 'Notify on error',
            description: 'Send a desktop notification when a fetch fails',
            default: true,
          },
          {
            name: 'refreshInterval',
            type: 'select',
            label: 'Refresh Interval',
            options: [
              { label: 'Every 10 seconds', value: '10' },
              { label: 'Every 30 seconds', value: '30' },
              { label: 'Every 60 seconds', value: '60' },
              { label: 'Every 5 minutes', value: '300' },
            ],
            default: '30',
          },
        ],
      },
    };
  }

  // Step 3: Preferences (final)
  if (args.stepId === 'preferences') {
    s.config.notifyOnError = args.values.notifyOnError !== false;
    s.config.refreshInterval = parseInt(String(args.values.refreshInterval || '30'), 10);

    // Persist the complete configuration
    store.set('config', s.config);

    return { status: 'complete' };
  }

  return { status: 'error', errors: [{ field: '', message: 'Unknown step' }] };
}

function onSetupCancel(): void {
  // Reset config to defaults if setup is cancelled
  const s = getState();
  s.config = { ...DEFAULT_CONFIG };
}

// ─── Disconnect ─────────────────────────────────────────────────────
function onDisconnect(): void {
  // Clean up credentials when user disconnects the skill
  store.delete('config');
  const s = getState();
  s.config = { ...DEFAULT_CONFIG };
}

// ─── Options System ─────────────────────────────────────────────────
// Runtime-configurable settings the user can change without re-running setup.

function onListOptions(): { options: SkillOption[] } {
  const s = getState();
  return {
    options: [
      {
        name: 'refreshInterval',
        type: 'select',
        label: 'Refresh Interval',
        description: 'How often to fetch data',
        value: String(s.config.refreshInterval),
        options: [
          { label: 'Every 10 seconds', value: '10' },
          { label: 'Every 30 seconds', value: '30' },
          { label: 'Every 60 seconds', value: '60' },
          { label: 'Every 5 minutes', value: '300' },
        ],
      },
      {
        name: 'notifyOnError',
        type: 'boolean',
        label: 'Notify on Error',
        description: 'Send desktop notification on fetch failure',
        value: s.config.notifyOnError,
      },
      {
        name: 'verbose',
        type: 'boolean',
        label: 'Verbose Logging',
        description: 'Log extra debug information to the console',
        value: s.config.verbose,
      },
    ],
  };
}

function onSetOption(args: { name: string; value: unknown }): void {
  const s = getState();

  if (args.name === 'refreshInterval') {
    s.config.refreshInterval = parseInt(String(args.value), 10);
    // Re-register cron with new interval
    cron.unregister('refresh');
    cron.register('refresh', `*/${s.config.refreshInterval} * * * * *`);
  } else if (args.name === 'notifyOnError') {
    s.config.notifyOnError = args.value === true || args.value === 'true';
  } else if (args.name === 'verbose') {
    s.config.verbose = args.value === true || args.value === 'true';
  }

  store.set('config', s.config);
}

// ─── Helpers ────────────────────────────────────────────────────────

/** Publish current state to the frontend for real-time display */
function publishState(): void {
  const s = getState();
  state.setPartial({
    status: s.isRunning ? 'running' : 'stopped',
    fetchCount: s.fetchCount,
    errorCount: s.errorCount,
    lastFetchTime: s.lastFetchTime,
    refreshInterval: s.config.refreshInterval,
    platform: platform.os(),
  });
}

// Expose helpers on globalThis so tools and tests can call them
const _g = globalThis as Record<string, unknown>;
_g.publishState = publishState;

// Expose lifecycle hooks on globalThis so the REPL/runtime can call them.
// esbuild IIFE bundling traps function declarations in the closure scope.
_g.init = init;
_g.start = start;
_g.stop = stop;
_g.onCronTrigger = onCronTrigger;
_g.onSetupStart = onSetupStart;
_g.onSetupSubmit = onSetupSubmit;
_g.onSetupCancel = onSetupCancel;
_g.onListOptions = onListOptions;
_g.onSetOption = onSetOption;
_g.onSessionStart = onSessionStart;
_g.onSessionEnd = onSessionEnd;
_g.onDisconnect = onDisconnect;
