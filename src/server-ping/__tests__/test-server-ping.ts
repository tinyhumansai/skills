// test-server-ping.ts — Comprehensive tests for the server-ping skill.
// Runs via the V8 test harness.

// All globals (describe, it, assert*, setupSkillTest, callTool, etc.)
// are available from the harness scripts loaded before this file.

// Helpers to access the typed globals
const _describe = (globalThis as any).describe as (name: string, fn: () => void) => void;
const _it = (globalThis as any).it as (name: string, fn: () => void) => void;
const _assert = (globalThis as any).assert as (cond: unknown, msg?: string) => void;
const _assertEqual = (globalThis as any).assertEqual as (
  a: unknown,
  b: unknown,
  msg?: string
) => void;
const _assertNotNull = (globalThis as any).assertNotNull as (v: unknown, msg?: string) => void;
const _assertContains = (globalThis as any).assertContains as (
  h: string,
  n: string,
  msg?: string
) => void;
const _assertGreaterThan = (globalThis as any).assertGreaterThan as (
  a: number,
  b: number,
  msg?: string
) => void;
const _setup = (globalThis as any).setupSkillTest as (opts?: any) => void;
const _callTool = (globalThis as any).callTool as (name: string, args?: any) => any;
const _getMockState = (globalThis as any).getMockState as () => any;
const _mockFetchResponse = (globalThis as any).mockFetchResponse as (
  url: string,
  status: number,
  body: string
) => void;

// Default clean config to reset skill state between tests.
// Since the skill uses module-level CONFIG that persists across calls,
// we must explicitly provide a clean config via store so init() resets it.
const CLEAN_CONFIG = {
  serverUrl: '',
  pingIntervalSec: 10,
  notifyOnDown: true,
  notifyOnRecover: true,
  verboseLogging: false,
};

const _mockFetchError = (globalThis as any).mockFetchError as (url: string, msg?: string) => void;

/** Reset mocks + re-init with clean defaults. Call before each test group. */
function freshInit(overrides?: {
  config?: Record<string, unknown>;
  counters?: Record<string, unknown>;
  env?: Record<string, string>;
  platformOs?: string;
  fetchResponses?: Record<
    string,
    { status: number; headers?: Record<string, string>; body: string }
  >;
  fetchErrors?: Record<string, string>;
  peerSkills?: { id: string; name: string; version?: string; status?: string }[];
}): void {
  const stateData: Record<string, unknown> = {
    config: { ...CLEAN_CONFIG, ...(overrides?.config || {}) },
  };
  if (overrides?.counters) {
    stateData['counters'] = overrides.counters;
  }
  _setup({
    stateData,
    env: overrides?.env || {},
    platformOs: overrides?.platformOs,
    fetchResponses: overrides?.fetchResponses,
    peerSkills: overrides?.peerSkills,
  });
  // Set up fetch errors (network errors that throw)
  if (overrides?.fetchErrors) {
    for (const [url, msg] of Object.entries(overrides.fetchErrors)) {
      _mockFetchError(url, msg);
    }
  }
  // Reset skill module-level state that persists across tests.
  // These are global vars set by loadScript() in the skill source.
  (globalThis as any).PING_COUNT = 0;
  (globalThis as any).FAIL_COUNT = 0;
  (globalThis as any).CONSECUTIVE_FAILS = 0;
  (globalThis as any).WAS_DOWN = false;
  (globalThis as any).ACTIVE_SESSIONS = [];
  (globalThis as any).init();
}

// ─────────────────────────────────────────────────────────────────────────────
// init() tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('init()', () => {
  _it('should create ping_log table', () => {
    freshInit();
    const tables = (globalThis as any).__mockTables;
    _assert(tables['ping_log'], 'ping_log table should exist');
    const cols = tables['ping_log'].columns.map((c: any) => c.name);
    _assertContains(cols.join(','), 'id', 'should have id column');
    _assertContains(cols.join(','), 'timestamp', 'should have timestamp column');
    _assertContains(cols.join(','), 'latency_ms', 'should have latency_ms column');
    _assertContains(cols.join(','), 'success', 'should have success column');
  });

  _it('should load config from store if available', () => {
    freshInit({ config: { serverUrl: 'https://saved.example.com', pingIntervalSec: 30 } });
    const stats = _callTool('get-ping-stats');
    _assertEqual(stats.serverUrl, 'https://saved.example.com', 'should use saved URL');
  });

  _it('should fall back to BACKEND_URL env var', () => {
    freshInit({ env: { BACKEND_URL: 'https://env.example.com/api' } });
    const stats = _callTool('get-ping-stats');
    _assertEqual(stats.serverUrl, 'https://env.example.com/api', 'should use env URL');
  });

  _it('should load persisted counters', () => {
    freshInit({
      config: { serverUrl: 'https://test.com' },
      counters: { pingCount: 42, failCount: 3 },
    });
    const stats = _callTool('get-ping-stats');
    _assertEqual(stats.totalPings, 42, 'should restore ping count');
    _assertEqual(stats.totalFailures, 3, 'should restore fail count');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// start() tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('start()', () => {
  _it('should register cron when URL is configured', () => {
    freshInit({ config: { serverUrl: 'https://test.com' } });
    (globalThis as any).start();
    const mock = _getMockState();
    _assert(mock.cronSchedules['ping'], 'should register ping cron');
    _assertContains(mock.cronSchedules['ping'], '*/10', 'default 10s interval');
  });

  _it('should not register cron without URL', () => {
    freshInit();
    (globalThis as any).start();
    const mock = _getMockState();
    _assertEqual(Object.keys(mock.cronSchedules).length, 0, 'should not register cron without URL');
  });

  _it('should use custom interval from config', () => {
    freshInit({ config: { serverUrl: 'https://test.com', pingIntervalSec: 30 } });
    (globalThis as any).start();
    const mock = _getMockState();
    _assertContains(mock.cronSchedules['ping'], '*/30', 'should use 30s interval');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Setup flow tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Setup flow', () => {
  _it('onSetupStart should return server-config step', () => {
    freshInit();
    const result = (globalThis as any).onSetupStart();
    _assertEqual(result.step.id, 'server-config', 'step id');
    _assert(result.step.fields.length >= 2, 'should have at least 2 fields');
    const fieldNames = result.step.fields.map((f: any) => f.name);
    _assertContains(fieldNames.join(','), 'serverUrl');
    _assertContains(fieldNames.join(','), 'pingIntervalSec');
  });

  _it('onSetupStart should pre-fill BACKEND_URL from env', () => {
    freshInit({ env: { BACKEND_URL: 'https://prefill.example.com' } });
    const result = (globalThis as any).onSetupStart();
    const urlField = result.step.fields.find((f: any) => f.name === 'serverUrl');
    _assertEqual(urlField.default, 'https://prefill.example.com', 'should pre-fill from env');
  });

  _it('onSetupSubmit should validate empty URL', () => {
    freshInit();
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'server-config',
      values: { serverUrl: '', pingIntervalSec: '10' },
    });
    _assertEqual(result.status, 'error', 'should return error');
    _assert(result.errors.length > 0, 'should have errors');
    _assertEqual(result.errors[0].field, 'serverUrl');
  });

  _it('onSetupSubmit should validate URL protocol', () => {
    freshInit();
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'server-config',
      values: { serverUrl: 'ftp://bad.com', pingIntervalSec: '10' },
    });
    _assertEqual(result.status, 'error', 'should reject non-http URL');
  });

  _it('onSetupSubmit step 1 should return next step', () => {
    freshInit();
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'server-config',
      values: { serverUrl: 'https://good.example.com', pingIntervalSec: '30' },
    });
    _assertEqual(result.status, 'next', 'should return next');
    _assertEqual(result.nextStep.id, 'notification-config');
  });

  _it('onSetupSubmit step 2 should complete', () => {
    freshInit();
    // Step 1
    (globalThis as any).onSetupSubmit({
      stepId: 'server-config',
      values: { serverUrl: 'https://complete.example.com', pingIntervalSec: '10' },
    });
    // Step 2
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'notification-config',
      values: { notifyOnDown: true, notifyOnRecover: false },
    });
    _assertEqual(result.status, 'complete', 'should complete');
    // Verify config was persisted
    const mock = _getMockState();
    _assert(mock.store['config'], 'config should be persisted to store');
    _assert(mock.dataFiles['config.json'], 'config.json should be written to data');
  });

  _it('onSetupSubmit should error on unknown step', () => {
    freshInit();
    const result = (globalThis as any).onSetupSubmit({ stepId: 'nonexistent', values: {} });
    _assertEqual(result.status, 'error');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Ping logic tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Ping logic', () => {
  _it('successful ping should log to DB', () => {
    freshInit({
      config: { serverUrl: 'https://healthy.com' },
      fetchResponses: { 'https://healthy.com': { status: 200, body: '{"ok":true}' } },
    });
    (globalThis as any).start();
    (globalThis as any).onCronTrigger('ping');
    const row = (globalThis as any).db.get(
      'SELECT status, success, url FROM ping_log ORDER BY id DESC LIMIT 1',
      []
    );
    _assertNotNull(row, 'should have a ping log row');
    _assertEqual(row.status, 200, 'status should be 200');
    _assertEqual(row.success, 1, 'should be successful');
    _assertEqual(row.url, 'https://healthy.com');
  });

  _it('failed ping should increment fail count', () => {
    freshInit({
      config: { serverUrl: 'https://down.com' },
      fetchResponses: {
        'https://down.com': { status: 500, body: '{"error":"Internal Server Error"}' },
      },
    });
    (globalThis as any).start();
    (globalThis as any).onCronTrigger('ping');
    const stats = _callTool('get-ping-stats');
    _assertEqual(stats.totalFailures, 1, 'fail count should be 1');
    _assertEqual(stats.consecutiveFailures, 1, 'consecutive fails should be 1');
  });

  _it('should notify on server down (network error)', () => {
    freshInit({
      config: { serverUrl: 'https://down.com' },
      fetchErrors: { 'https://down.com': 'Connection refused' },
    });
    (globalThis as any).start();
    (globalThis as any).onCronTrigger('ping');
    const mock = _getMockState();
    _assertGreaterThan(mock.notifications.length, 0, 'should send notification on down');
    _assertContains(mock.notifications[0].title, 'Down', 'notification title should mention Down');
  });

  _it('should notify on recovery after downtime', () => {
    freshInit({
      config: { serverUrl: 'https://flaky.com' },
      fetchErrors: { 'https://flaky.com': 'Connection refused' },
    });
    (globalThis as any).start();
    // First ping fails (network error)
    (globalThis as any).onCronTrigger('ping');
    // Remove the error and set a success response
    (globalThis as any).__mockFetchErrors = {};
    _mockFetchResponse('https://flaky.com', 200, '{"ok":true}');
    (globalThis as any).onCronTrigger('ping');
    const mock = _getMockState();
    _assertGreaterThan(mock.notifications.length, 1, 'should have recovery notification');
    _assertContains(mock.notifications[1].title, 'Recovered');
  });

  _it('should skip non-ping cron triggers', () => {
    freshInit({ config: { serverUrl: 'https://test.com' } });
    (globalThis as any).onCronTrigger('some-other-schedule');
    const stats = _callTool('get-ping-stats');
    _assertEqual(stats.totalPings, 0, 'should not increment for other schedules');
  });

  _it('should publish state to frontend', () => {
    freshInit({
      config: { serverUrl: 'https://test.com' },
      fetchResponses: { 'https://test.com': { status: 200, body: '{"ok":true}' } },
    });
    (globalThis as any).start();
    (globalThis as any).onCronTrigger('ping');
    const mock = _getMockState();
    _assertEqual(mock.stateValues['status'], 'healthy');
    _assertEqual(mock.stateValues['pingCount'], 1);
    _assertEqual(mock.stateValues['serverUrl'], 'https://test.com');
  });

  _it('should write ping-log.txt data file', () => {
    freshInit({
      config: { serverUrl: 'https://test.com' },
      fetchResponses: { 'https://test.com': { status: 200, body: '{"ok":true}' } },
    });
    (globalThis as any).start();
    (globalThis as any).onCronTrigger('ping');
    const mock = _getMockState();
    _assert(mock.dataFiles['ping-log.txt'], 'should write ping-log.txt');
    _assertContains(mock.dataFiles['ping-log.txt'], 'Ping Log');
  });

  _it('should not send notification on mobile', () => {
    freshInit({
      platformOs: 'android',
      config: { serverUrl: 'https://down.com' },
      fetchErrors: { 'https://down.com': 'Connection refused' },
    });
    (globalThis as any).start();
    (globalThis as any).onCronTrigger('ping');
    const mock = _getMockState();
    _assertEqual(mock.notifications.length, 0, 'should skip notification on mobile');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Tools tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Tools', () => {
  _it('get-ping-stats should return stats object', () => {
    freshInit({ config: { serverUrl: 'https://test.com' } });
    const stats = _callTool('get-ping-stats');
    _assertNotNull(stats, 'should return stats');
    _assertEqual(stats.serverUrl, 'https://test.com');
    _assertEqual(stats.uptimePercent, 100, '100% uptime with no pings');
    _assertNotNull(stats.platform, 'should include platform');
  });

  _it('get-ping-history should return history array', () => {
    freshInit({
      config: { serverUrl: 'https://test.com' },
      fetchResponses: { 'https://test.com': { status: 200, body: '{"ok":true}' } },
    });
    (globalThis as any).start();
    (globalThis as any).onCronTrigger('ping');
    (globalThis as any).onCronTrigger('ping');
    const history = _callTool('get-ping-history', { limit: '5' });
    _assertEqual(history.count, 2, 'should have 2 entries');
    _assert(Array.isArray(history.history), 'history should be an array');
  });

  _it('get-ping-history should respect limit', () => {
    freshInit({
      config: { serverUrl: 'https://test.com' },
      fetchResponses: { 'https://test.com': { status: 200, body: '{"ok":true}' } },
    });
    (globalThis as any).start();
    for (let i = 0; i < 5; i++) {
      (globalThis as any).onCronTrigger('ping');
    }
    const history = _callTool('get-ping-history', { limit: '3' });
    _assertEqual(history.count, 3, 'should limit to 3');
  });

  _it('ping-now should trigger immediate ping', () => {
    freshInit({
      config: { serverUrl: 'https://test.com' },
      fetchResponses: { 'https://test.com': { status: 200, body: '{"ok":true}' } },
    });
    const result = _callTool('ping-now');
    _assertEqual(result.triggered, true);
    _assertGreaterThan(result.pingNumber, 0, 'should have ping number');
    _assertNotNull(result.result, 'should return ping result');
  });

  _it('update-server-url should change URL', () => {
    freshInit({ config: { serverUrl: 'https://old.com' } });
    const result = _callTool('update-server-url', { url: 'https://new.com' });
    _assertEqual(result.success, true);
    _assertEqual(result.oldUrl, 'https://old.com');
    _assertEqual(result.newUrl, 'https://new.com');
    const stats = _callTool('get-ping-stats');
    _assertEqual(stats.serverUrl, 'https://new.com');
  });

  _it('update-server-url should reject invalid URL', () => {
    freshInit({ config: { serverUrl: 'https://test.com' } });
    const result = _callTool('update-server-url', { url: 'not-a-url' });
    _assert(result.error, 'should return error for invalid URL');
  });

  _it('list-peer-skills should return skills list', () => {
    freshInit({
      config: { serverUrl: 'https://test.com' },
      peerSkills: [
        { id: 'telegram', name: 'Telegram', version: '1.0.0' },
        { id: 'wallet-watch', name: 'Wallet Watch', version: '2.0.0' },
      ],
    });
    const result = _callTool('list-peer-skills');
    _assertEqual(result.skills.length, 2, 'should list 2 peers');
    _assertEqual(result.skills[0].id, 'telegram');
  });

  _it('read-config should return config file content', () => {
    freshInit({ config: { serverUrl: 'https://test.com' } });
    // Setup flow writes config.json
    (globalThis as any).onSetupSubmit({
      stepId: 'server-config',
      values: { serverUrl: 'https://test.com', pingIntervalSec: '10' },
    });
    (globalThis as any).onSetupSubmit({
      stepId: 'notification-config',
      values: { notifyOnDown: true, notifyOnRecover: true },
    });
    const result = _callTool('read-config');
    _assertNotNull(result, 'should return config');
    _assertContains(JSON.stringify(result), 'serverUrl');
  });

  _it('read-config should handle missing file', () => {
    freshInit();
    const result = _callTool('read-config');
    _assert(typeof result === 'object' && result.error, 'should return error when no config file');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Session lifecycle tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Sessions', () => {
  _it('onSessionStart should track session', () => {
    freshInit({
      config: { serverUrl: 'https://test.com' },
      fetchResponses: { 'https://test.com': { status: 200, body: '{"ok":true}' } },
    });
    (globalThis as any).start();
    (globalThis as any).onSessionStart({ sessionId: 'sess-1' });
    (globalThis as any).onCronTrigger('ping');
    const mock = _getMockState();
    _assertEqual(mock.stateValues['activeSessions'], 1, 'should track 1 session');
  });

  _it('onSessionEnd should remove session', () => {
    freshInit({
      config: { serverUrl: 'https://test.com' },
      fetchResponses: { 'https://test.com': { status: 200, body: '{"ok":true}' } },
    });
    (globalThis as any).start();
    (globalThis as any).onSessionStart({ sessionId: 'sess-1' });
    (globalThis as any).onSessionStart({ sessionId: 'sess-2' });
    (globalThis as any).onSessionEnd({ sessionId: 'sess-1' });
    (globalThis as any).onCronTrigger('ping');
    const mock = _getMockState();
    _assertEqual(mock.stateValues['activeSessions'], 1, 'should have 1 session left');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Options tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Options', () => {
  _it('onListOptions should return all options', () => {
    freshInit({ config: { serverUrl: 'https://test.com' } });
    const result = (globalThis as any).onListOptions();
    _assert(result.options.length >= 4, 'should have at least 4 options');
    const names = result.options.map((o: any) => o.name);
    _assertContains(names.join(','), 'pingIntervalSec');
    _assertContains(names.join(','), 'notifyOnDown');
    _assertContains(names.join(','), 'verboseLogging');
  });

  _it('onSetOption should change ping interval and re-register cron', () => {
    freshInit({ config: { serverUrl: 'https://test.com' } });
    (globalThis as any).start();
    let mock = _getMockState();
    _assertContains(mock.cronSchedules['ping'], '*/10', 'initial interval');
    (globalThis as any).onSetOption({ name: 'pingIntervalSec', value: '60' });
    mock = _getMockState();
    _assertContains(mock.cronSchedules['ping'], '*/60', 'updated interval');
  });

  _it('onSetOption should toggle boolean options', () => {
    freshInit({ config: { serverUrl: 'https://test.com' } });
    (globalThis as any).onSetOption({ name: 'verboseLogging', value: true });
    const result = (globalThis as any).onListOptions();
    const verbose = result.options.find((o: any) => o.name === 'verboseLogging');
    _assertEqual(verbose.value, true, 'verbose should be true');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// stop() tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('stop()', () => {
  _it('should unregister cron and persist counters', () => {
    freshInit({
      config: { serverUrl: 'https://test.com' },
      fetchResponses: { 'https://test.com': { status: 200, body: '{"ok":true}' } },
    });
    (globalThis as any).start();
    (globalThis as any).onCronTrigger('ping');
    (globalThis as any).stop();
    const mock = _getMockState();
    _assertEqual(Object.keys(mock.cronSchedules).length, 0, 'cron should be unregistered');
    _assert(mock.store['counters'], 'counters should be persisted');
    _assertEqual(mock.stateValues['status'], 'stopped');
  });
});
