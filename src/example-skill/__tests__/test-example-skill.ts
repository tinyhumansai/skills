/**
 * Comprehensive tests for example-skill.
 * Covers all lifecycle hooks, setup flow, options, tools, and error handling.
 */

import type { ExampleConfig } from '../types';

const DEFAULT_CONFIG: ExampleConfig = {
  serverUrl: '',
  apiKey: '',
  refreshInterval: 30,
  notifyOnError: true,
  webhookUrl: '',
  verbose: false,
};

const MOCK_URL = 'https://api.example.com';

function freshInit(overrides?: Partial<ExampleConfig>): void {
  const config = { ...DEFAULT_CONFIG, ...overrides };
  setupSkillTest({
    storeData: overrides ? { config } : {},
    fetchResponses: {
      [MOCK_URL]: { status: 200, body: '{"ok":true}' },
    },
  });
  init();
}

// ─── init() ──────────────────────────────────────────────────────────

_describe('init()', () => {
  _it('should create logs table', () => {
    freshInit();
    // Table should exist — inserting should not throw
    db.exec('INSERT INTO logs (level, message, created_at) VALUES (?, ?, ?)', [
      'test',
      'hello',
      '2025-01-01T00:00:00Z',
    ]);
    const row = db.get('SELECT * FROM logs WHERE level = ?', ['test']);
    _assertNotNull(row);
  });

  _it('should load config from store', () => {
    freshInit({ serverUrl: 'https://saved.example.com', apiKey: 'saved-key' });
    const s = globalThis.getSkillState();
    _assertEqual(s.config.serverUrl, 'https://saved.example.com');
    _assertEqual(s.config.apiKey, 'saved-key');
  });

  _it('should use defaults when no saved config', () => {
    freshInit();
    const s = globalThis.getSkillState();
    _assertEqual(s.config.serverUrl, '');
    _assertEqual(s.config.refreshInterval, 30);
    _assertTrue(s.config.notifyOnError);
  });
});

// ─── start() / stop() ────────────────────────────────────────────────

_describe('start()', () => {
  _it('should register cron schedule', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    start();
    const ms = getMockState();
    _assertNotNull(ms.cronSchedules['refresh']);
    _assertEqual(ms.cronSchedules['refresh'], '*/30 * * * * *');
  });

  _it('should publish initial state', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    start();
    const ms = getMockState();
    _assertEqual(ms.state['status'], 'running');
  });
});

_describe('stop()', () => {
  _it('should unregister cron and persist config', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    start();
    stop();

    const ms = getMockState();
    _assertNull(ms.cronSchedules['refresh'] ?? null);
    _assertNotNull(ms.store['config']);
  });

  _it('should write last-state.json data file', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    start();
    stop();

    const ms = getMockState();
    _assertNotNull(ms.dataFiles['last-state.json']);
    const lastState = JSON.parse(ms.dataFiles['last-state.json']);
    _assertNotNull(lastState.stoppedAt);
  });
});

// ─── Setup Flow ──────────────────────────────────────────────────────

_describe('Setup Flow', () => {
  _it('should return credentials step on start', () => {
    freshInit();
    const result = callTool('get-status', {});
    // Now test setup
    const step1 = onSetupStart();
    _assertEqual(step1.step.id, 'credentials');
    _assertEqual(step1.step.fields.length, 2);
  });

  _it('should validate required fields', () => {
    freshInit();
    onSetupStart();
    const result = onSetupSubmit({ stepId: 'credentials', values: {} });
    _assertEqual(result.status, 'error');
    _assertTrue(result.errors!.length > 0);
  });

  _it('should advance to webhook step', () => {
    freshInit();
    onSetupStart();
    const result = onSetupSubmit({
      stepId: 'credentials',
      values: { serverUrl: MOCK_URL, apiKey: 'test-key' },
    });
    _assertEqual(result.status, 'next');
    _assertEqual(result.nextStep!.id, 'webhook');
  });

  _it('should complete full 3-step wizard', () => {
    freshInit();
    onSetupStart();

    // Step 1
    const r1 = onSetupSubmit({
      stepId: 'credentials',
      values: { serverUrl: MOCK_URL, apiKey: 'test-key' },
    });
    _assertEqual(r1.status, 'next');

    // Step 2
    const r2 = onSetupSubmit({
      stepId: 'webhook',
      values: { webhookUrl: 'https://hooks.example.com' },
    });
    _assertEqual(r2.status, 'next');
    _assertEqual(r2.nextStep!.id, 'preferences');

    // Step 3
    const r3 = onSetupSubmit({
      stepId: 'preferences',
      values: { notifyOnError: true, refreshInterval: '60' },
    });
    _assertEqual(r3.status, 'complete');

    // Verify config was saved
    const s = globalThis.getSkillState();
    _assertEqual(s.config.serverUrl, MOCK_URL);
    _assertEqual(s.config.refreshInterval, 60);
  });

  _it('should reset config on cancel', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    onSetupCancel();
    const s = globalThis.getSkillState();
    _assertEqual(s.config.serverUrl, '');
    _assertEqual(s.config.apiKey, '');
  });
});

// ─── Options ─────────────────────────────────────────────────────────

_describe('Options', () => {
  _it('should list all options', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key', refreshInterval: 30 });
    const result = onListOptions();
    _assertEqual(result.options.length, 3);
    const names = result.options.map((o: SkillOption) => o.name);
    _assertTrue(names.indexOf('refreshInterval') >= 0);
    _assertTrue(names.indexOf('notifyOnError') >= 0);
    _assertTrue(names.indexOf('verbose') >= 0);
  });

  _it('should update refresh interval and re-register cron', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    start();

    onSetOption({ name: 'refreshInterval', value: '60' });

    const s = globalThis.getSkillState();
    _assertEqual(s.config.refreshInterval, 60);

    const ms = getMockState();
    _assertEqual(ms.cronSchedules['refresh'], '*/60 * * * * *');
  });

  _it('should toggle notifyOnError', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key', notifyOnError: true });
    onSetOption({ name: 'notifyOnError', value: false });
    const s = globalThis.getSkillState();
    _assertFalse(s.config.notifyOnError);
  });
});

// ─── Tools ───────────────────────────────────────────────────────────

_describe('Tools', () => {
  _it('get-status should return running state', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    start();
    const result = callTool('get-status', {});
    _assertEqual(result.status, 'running');
    _assertEqual(result.fetchCount, 0);
  });

  _it('get-status verbose should include config', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    start();
    const result = callTool('get-status', { verbose: 'true' });
    _assertNotNull(result.config);
    _assertEqual(result.config.serverUrl, MOCK_URL);
  });

  _it('fetch-data should return response', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    const result = callTool('fetch-data', {});
    _assertEqual(result.status, 200);
    _assertEqual(result.body, '{"ok":true}');
  });

  _it('fetch-data should error when no URL configured', () => {
    freshInit();
    const result = callTool('fetch-data', {});
    _assertNotNull(result.error);
  });

  _it('fetch-data should handle network errors', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    mockFetchError(MOCK_URL, 'Connection refused');
    const result = callTool('fetch-data', {});
    _assertNotNull(result.error);
  });

  _it('query-logs should return empty initially', () => {
    freshInit();
    const result = callTool('query-logs', { limit: 5 });
    _assertEqual(result.count, 0);
  });

  _it('list-peers should return skill list', () => {
    freshInit();
    const result = callTool('list-peers', {});
    _assertEqual(result.count, 0);
  });
});

// ─── Cron Trigger ────────────────────────────────────────────────────

_describe('onCronTrigger', () => {
  _it('should fetch and increment counter on success', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    start();
    onCronTrigger('refresh');

    const s = globalThis.getSkillState();
    _assertEqual(s.fetchCount, 1);
    _assertEqual(s.errorCount, 0);
    _assertNotNull(s.lastFetchTime);
  });

  _it('should increment errorCount and notify on failure', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key', notifyOnError: true });
    start();
    mockFetchError(MOCK_URL, 'Server down');
    onCronTrigger('refresh');

    const s = globalThis.getSkillState();
    _assertEqual(s.errorCount, 1);
    _assertEqual(s.fetchCount, 0);

    const ms = getMockState();
    _assertTrue(ms.notifications.length > 0);
  });

  _it('should not notify when notifyOnError is false', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key', notifyOnError: false });
    start();
    mockFetchError(MOCK_URL, 'Server down');
    onCronTrigger('refresh');

    const ms = getMockState();
    _assertEqual(ms.notifications.length, 0);
  });

  _it('should skip when serverUrl is empty', () => {
    freshInit();
    start();
    onCronTrigger('refresh');
    const s = globalThis.getSkillState();
    _assertEqual(s.fetchCount, 0);
  });
});

// ─── Disconnect ──────────────────────────────────────────────────────

_describe('onDisconnect', () => {
  _it('should clear stored config', () => {
    freshInit({ serverUrl: MOCK_URL, apiKey: 'key' });
    onDisconnect();

    const ms = getMockState();
    _assertNull(ms.store['config'] ?? null);

    const s = globalThis.getSkillState();
    _assertEqual(s.config.serverUrl, '');
  });
});

// ─── Data I/O ────────────────────────────────────────────────────────

_describe('Data I/O', () => {
  _it('should round-trip data files', () => {
    freshInit();
    data.write('test.json', '{"hello":"world"}');
    const content = data.read('test.json');
    _assertNotNull(content);
    _assertEqual(content, '{"hello":"world"}');
  });

  _it('should return null for missing files', () => {
    freshInit();
    const content = data.read('nonexistent.json');
    _assertNull(content);
  });
});

// ─── Platform ────────────────────────────────────────────────────────

_describe('Platform', () => {
  _it('should return OS', () => {
    freshInit();
    const os = platform.os();
    _assertNotNull(os);
  });

  _it('should return empty string for unset env var', () => {
    freshInit();
    const val = platform.env('NONEXISTENT_VAR');
    _assertEqual(val, '');
  });
});
