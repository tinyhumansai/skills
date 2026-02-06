// Import all tools
// Import to initialize state
import { getSkillState } from './skill-state';
import { getPingHistoryTool } from './tools/get-ping-history';
import { getPingStatsTool } from './tools/get-ping-stats';
import { listPeerSkillsTool } from './tools/list-peer-skills';
import { pingNowTool } from './tools/ping-now';
import { readConfigTool } from './tools/read-config';
import { updateServerUrlTool } from './tools/update-server-url';
import type { SkillConfig } from './types';

// server-ping/index.ts
// Comprehensive demo skill showcasing all V8 runtime capabilities:
//   Setup flow, DB (SQLite), Store (KV), State (frontend pub), Data (file I/O),
//   Net (HTTP), setInterval (scheduling), Platform (OS/notify), Skills (interop),
//   Options, Tools, and Session lifecycle.

// ---------------------------------------------------------------------------
// Lifecycle hooks
// ---------------------------------------------------------------------------

function init(): void {
  console.log(`[server-ping] Initializing on ${platform.os()}`);
  const s = getSkillState();

  // Create DB table for ping history
  db.exec(
    `CREATE TABLE IF NOT EXISTS ping_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT NOT NULL,
      url TEXT NOT NULL,
      status INTEGER,
      latency_ms INTEGER,
      success INTEGER NOT NULL,
      error TEXT
    )`,
    []
  );

  // Load persisted config from store
  const saved = store.get('config') as Partial<SkillConfig> | null;
  if (saved) {
    s.config.serverUrl = saved.serverUrl ?? s.config.serverUrl;
    s.config.pingIntervalSec = saved.pingIntervalSec ?? s.config.pingIntervalSec;
    s.config.notifyOnDown = saved.notifyOnDown ?? s.config.notifyOnDown;
    s.config.notifyOnRecover = saved.notifyOnRecover ?? s.config.notifyOnRecover;
    s.config.verboseLogging = saved.verboseLogging ?? s.config.verboseLogging;
  }

  // Fall back to the host's backend URL if no server URL is configured yet
  if (!s.config.serverUrl) {
    // Try both BACKEND_URL and VITE_BACKEND_URL (Vite uses VITE_ prefix)
    const envUrl = platform.env('BACKEND_URL') || platform.env('VITE_BACKEND_URL');
    if (envUrl) {
      s.config.serverUrl = envUrl;
      console.log(`[server-ping] Using BACKEND_URL from env: ${envUrl}`);
    }
  }

  // Load counters from store
  const counters = store.get('counters') as { pingCount?: number; failCount?: number } | null;
  if (counters) {
    s.pingCount = counters.pingCount ?? 0;
    s.failCount = counters.failCount ?? 0;
  }

  console.log(`[server-ping] Config loaded — target: ${s.config.serverUrl}`);
}

function start(): void {
  const s = getSkillState();

  if (!s.config.serverUrl) {
    console.warn('[server-ping] No server URL configured — waiting for setup');
    return;
  }

  const intervalMs = s.config.pingIntervalSec * 1000;
  console.log(
    `[server-ping] Starting — ping every ${s.config.pingIntervalSec}s (using setInterval)`
  );

  // Clear any existing interval
  if (s.pingIntervalId !== null) {
    clearInterval(s.pingIntervalId);
  }

  // Start the ping interval (cast to number for browser-like V8 environment)
  s.pingIntervalId = setInterval(() => {
    doPing();
  }, intervalMs) as unknown as number;

  // Do an immediate first ping
  doPing();

  // Publish initial state to frontend
  publishState();
}

function stop(): void {
  console.log('[server-ping] Stopping');
  const s = getSkillState();

  // Clear the ping interval
  if (s.pingIntervalId !== null) {
    clearInterval(s.pingIntervalId);
    s.pingIntervalId = null;
  }

  // Persist counters
  store.set('counters', { pingCount: s.pingCount, failCount: s.failCount });

  state.set('status', 'stopped');
}

// ---------------------------------------------------------------------------
// Setup flow (multi-step)
// ---------------------------------------------------------------------------

function onSetupStart(): SetupStartResult {
  console.log('[server-ping] onSetupStart');
  // Pre-fill with the host's backend URL so the user doesn't have to type it
  const defaultUrl = platform.env('BACKEND_URL') || platform.env('VITE_BACKEND_URL') || '';

  return {
    step: {
      id: 'server-config',
      title: 'Server Configuration',
      description: 'Enter the server URL to monitor and choose a ping interval.',
      fields: [
        {
          name: 'serverUrl',
          type: 'text',
          label: 'Server URL',
          description: 'Full URL to ping (e.g. https://api.example.com/health)',
          required: true,
          default: defaultUrl,
          placeholder: 'https://api.example.com/health',
        },
        {
          name: 'pingIntervalSec',
          type: 'select',
          label: 'Ping Interval',
          description: 'How often to check the server',
          required: true,
          default: '10',
          options: [
            { label: 'Every 5 seconds', value: '5' },
            { label: 'Every 10 seconds', value: '10' },
            { label: 'Every 30 seconds', value: '30' },
            { label: 'Every 60 seconds', value: '60' },
          ],
        },
      ],
    },
  };
}

function onSetupSubmit(args: {
  stepId: string;
  values: Record<string, unknown>;
}): SetupSubmitResult {
  const { stepId, values } = args;
  const s = getSkillState();

  if (stepId === 'server-config') {
    // Validate URL
    const url = ((values.serverUrl as string) ?? '').trim();
    if (!url) {
      return {
        status: 'error',
        errors: [{ field: 'serverUrl', message: 'Server URL is required' }],
      };
    }
    if (!url.startsWith('http')) {
      return {
        status: 'error',
        errors: [{ field: 'serverUrl', message: 'URL must start with http:// or https://' }],
      };
    }

    // Store values and move to next step
    s.config.serverUrl = url;
    s.config.pingIntervalSec = parseInt(values.pingIntervalSec as string) || 10;

    return {
      status: 'next',
      nextStep: {
        id: 'notification-config',
        title: 'Notification Preferences',
        description: 'Choose when to receive desktop notifications.',
        fields: [
          {
            name: 'notifyOnDown',
            type: 'boolean',
            label: 'Notify when server goes down',
            description: 'Send a desktop notification when the server becomes unreachable',
            required: false,
            default: true,
          },
          {
            name: 'notifyOnRecover',
            type: 'boolean',
            label: 'Notify when server recovers',
            description: 'Send a desktop notification when the server comes back online',
            required: false,
            default: true,
          },
        ],
      },
    };
  }

  if (stepId === 'notification-config') {
    s.config.notifyOnDown = (values.notifyOnDown as boolean) ?? true;
    s.config.notifyOnRecover = (values.notifyOnRecover as boolean) ?? true;

    // Persist full config to store
    store.set('config', s.config);

    // Write a human-readable config file to data dir
    data.write('config.json', JSON.stringify(s.config, null, 2));

    console.log(`[server-ping] Setup complete — monitoring ${s.config.serverUrl}`);

    return { status: 'complete' };
  }

  return { status: 'error', errors: [{ field: '', message: `Unknown setup step: ${stepId}` }] };
}

function onSetupCancel(): void {
  console.log('[server-ping] Setup cancelled');
}

// ---------------------------------------------------------------------------
// Options (runtime-configurable)
// ---------------------------------------------------------------------------

function onListOptions(): { options: SkillOption[] } {
  const s = getSkillState();
  return {
    options: [
      {
        name: 'pingIntervalSec',
        type: 'select',
        label: 'Ping interval',
        description: 'How often to check the server',
        value: String(s.config.pingIntervalSec),
        options: [
          { label: 'Every 5 seconds', value: '5' },
          { label: 'Every 10 seconds', value: '10' },
          { label: 'Every 30 seconds', value: '30' },
          { label: 'Every 60 seconds', value: '60' },
        ],
      },
      {
        name: 'notifyOnDown',
        type: 'boolean',
        label: 'Notify on server down',
        description: 'Send desktop notification when server is unreachable',
        value: s.config.notifyOnDown,
      },
      {
        name: 'notifyOnRecover',
        type: 'boolean',
        label: 'Notify on recovery',
        description: 'Send desktop notification when server recovers',
        value: s.config.notifyOnRecover,
      },
      {
        name: 'verboseLogging',
        type: 'boolean',
        label: 'Verbose logging',
        description: 'Log every ping result to console',
        value: s.config.verboseLogging,
      },
    ],
  };
}

function onSetOption(args: { name: string; value: unknown }): void {
  const { name, value } = args;
  const s = getSkillState();

  if (name === 'pingIntervalSec') {
    const newInterval = parseInt(value as string) || 10;
    s.config.pingIntervalSec = newInterval;

    // Restart interval with new timing
    if (s.pingIntervalId !== null) {
      clearInterval(s.pingIntervalId);
      const intervalMs = newInterval * 1000;
      s.pingIntervalId = setInterval(() => {
        doPing();
      }, intervalMs) as unknown as number;
    }
    console.log(`[server-ping] Ping interval changed to ${newInterval}s`);
  } else if (name === 'notifyOnDown') {
    s.config.notifyOnDown = !!value;
  } else if (name === 'notifyOnRecover') {
    s.config.notifyOnRecover = !!value;
  } else if (name === 'verboseLogging') {
    s.config.verboseLogging = !!value;
  }

  // Persist updated config
  store.set('config', s.config);
  publishState();
  console.log(`[server-ping] Option '${name}' set to ${value}`);
}

// ---------------------------------------------------------------------------
// Session lifecycle
// ---------------------------------------------------------------------------

function onSessionStart(args: { sessionId: string }): void {
  const { sessionId } = args;
  const s = getSkillState();
  s.activeSessions.push(sessionId);
  console.log(`[server-ping] Session started: ${sessionId} (active: ${s.activeSessions.length})`);
}

function onSessionEnd(args: { sessionId: string }): void {
  const { sessionId } = args;
  const s = getSkillState();
  s.activeSessions = s.activeSessions.filter(sid => sid !== sessionId);
  console.log(`[server-ping] Session ended: ${sessionId} (active: ${s.activeSessions.length})`);
}

// ---------------------------------------------------------------------------
// Cron handler (legacy — now using setInterval instead)
// ---------------------------------------------------------------------------

function onCronTrigger(_scheduleId: string): void {
  // No longer using cron — ping is driven by setInterval in start()
  // This handler is kept for backwards compatibility
}

function doPing(): void {
  const s = getSkillState();
  s.pingCount++;
  const timestamp = new Date().toISOString();
  const startTime = Date.now();

  try {
    const response = net.fetch(s.config.serverUrl, { method: 'GET', timeout: 10 });

    const latencyMs = Date.now() - startTime;
    const success = response.status >= 200 && response.status < 400;

    if (!success) {
      s.failCount++;
      s.consecutiveFails++;
    } else {
      // Check if recovering from downtime
      if (s.wasDown && s.config.notifyOnRecover) {
        sendNotification(
          'Server Recovered',
          `${s.config.serverUrl} is back online (was down for ${s.consecutiveFails} checks)`
        );
      }
      s.consecutiveFails = 0;
      s.wasDown = false;
    }

    if (s.config.verboseLogging) {
      console.log(`[server-ping] #${s.pingCount} ${response.status} ${latencyMs}ms`);
    }

    // Log to DB
    db.exec(
      'INSERT INTO ping_log (timestamp, url, status, latency_ms, success, error) VALUES (?, ?, ?, ?, ?, ?)',
      [timestamp, s.config.serverUrl, response.status, latencyMs, success ? 1 : 0, null]
    );
  } catch (e) {
    const latencyMs = Date.now() - startTime;
    s.failCount++;
    s.consecutiveFails++;

    console.error(`[server-ping] #${s.pingCount} FAILED: ${e}`);

    // Log failure to DB
    db.exec(
      'INSERT INTO ping_log (timestamp, url, status, latency_ms, success, error) VALUES (?, ?, ?, ?, ?, ?)',
      [timestamp, s.config.serverUrl, 0, latencyMs, 0, String(e)]
    );

    // Notify on first failure
    if (s.consecutiveFails === 1 && s.config.notifyOnDown) {
      s.wasDown = true;
      sendNotification('Server Down', `${s.config.serverUrl} is unreachable: ${e}`);
    }
  }

  // Persist counters periodically (every 10 pings)
  if (s.pingCount % 10 === 0) {
    store.set('counters', { pingCount: s.pingCount, failCount: s.failCount });
  }

  // Publish state to frontend
  publishState();

  // Append to data log file (last 100 entries summary)
  appendDataLog(timestamp);
}

// ---------------------------------------------------------------------------
// State publishing (real-time frontend updates)
// ---------------------------------------------------------------------------

function publishState(): void {
  const s = getSkillState();

  const uptimePct =
    s.pingCount > 0 ? Math.round(((s.pingCount - s.failCount) / s.pingCount) * 10000) / 100 : 100;

  // Get latest latency from DB
  const latest = db.get(
    'SELECT latency_ms, status, success FROM ping_log ORDER BY id DESC LIMIT 1',
    []
  ) as { latency_ms: number; status: number; success: number } | null;

  state.setPartial({
    status: s.consecutiveFails > 0 ? 'down' : 'healthy',
    pingCount: s.pingCount,
    failCount: s.failCount,
    consecutiveFails: s.consecutiveFails,
    uptimePercent: uptimePct,
    lastLatencyMs: latest ? latest.latency_ms : null,
    lastStatus: latest ? latest.status : null,
    serverUrl: s.config.serverUrl,
    activeSessions: s.activeSessions.length,
    platform: platform.os(),
  });
}

// Expose functions to globalThis for bundled tool modules
const _g = globalThis as Record<string, unknown>;
_g.doPing = doPing;
_g.publishState = publishState;

// ---------------------------------------------------------------------------
// Data file logging
// ---------------------------------------------------------------------------

function appendDataLog(timestamp: string): void {
  const recent = db.all(
    'SELECT timestamp, status, latency_ms, success, error FROM ping_log ORDER BY id DESC LIMIT 20',
    []
  ) as {
    timestamp: string;
    status: number;
    latency_ms: number;
    success: number;
    error: string | null;
  }[];

  const lines = ['# Ping Log (last 20 entries)', `# Generated: ${timestamp}`, ''];
  for (const r of recent) {
    const statusStr = r.success ? `OK ${r.status}` : 'FAIL';
    lines.push(
      `${r.timestamp} | ${statusStr} | ${r.latency_ms}ms${r.error ? ` | ${r.error}` : ''}`
    );
  }
  data.write('ping-log.txt', lines.join('\n'));
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

function sendNotification(title: string, body: string): void {
  const currentOs = platform.os();
  if (currentOs === 'android' || currentOs === 'ios') {
    console.log(`[server-ping] Notification (mobile, skipped): ${title} — ${body}`);
    return;
  }
  try {
    platform.notify(title, body);
  } catch (e) {
    console.warn(`[server-ping] Notification failed: ${e}`);
  }
}

// ---------------------------------------------------------------------------
// Tools (callable by AI and other skills)
// ---------------------------------------------------------------------------

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

const tools = [
  getPingStatsTool,
  getPingHistoryTool,
  pingNowTool,
  listPeerSkillsTool,
  updateServerUrlTool,
  readConfigTool,
];

const skill: Skill = {
  info: {
    id: 'server-ping',
    name: 'Server Ping',
    runtime: 'v8',
    entry: 'index.js',
    version: '2.2.0',
    description:
      'Monitors server health with configurable ping intervals using setInterval. Demos setup flow, DB, state, data, net, platform, skills interop, options, and tools.',
    auto_start: false,
    setup: { required: true, label: 'Configure Server Ping' },
  },
  tools,
  init,
  start,
  stop,
  onCronTrigger,
  onSetupStart,
  onSetupSubmit,
  onSetupCancel,
  onListOptions,
  onSetOption,
  onSessionStart,
  onSessionEnd,
};

export default skill;
