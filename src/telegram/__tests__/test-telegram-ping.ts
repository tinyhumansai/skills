// test-telegram-ping.ts — Tests for the telegram-ping tool.
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
const _mockFetchError = (globalThis as any).mockFetchError as (url: string, msg?: string) => void;

// Default clean config to reset skill state between tests.
const CLEAN_CONFIG = { apiId: 0, apiHash: '', phoneNumber: '', isAuthenticated: false };

/** Reset mocks + re-init with clean defaults. Call before each test group. */
function freshInit(overrides?: {
  config?: Record<string, unknown>;
  env?: Record<string, string>;
  fetchResponses?: Record<
    string,
    { status: number; headers?: Record<string, string>; body: string }
  >;
  fetchErrors?: Record<string, string>;
}): void {
  const stateData: Record<string, unknown> = {
    config: { ...CLEAN_CONFIG, ...(overrides?.config || {}) },
  };
  _setup({ stateData, env: overrides?.env || {}, fetchResponses: overrides?.fetchResponses });
  // Set up fetch errors (network errors that throw)
  if (overrides?.fetchErrors) {
    for (const [url, msg] of Object.entries(overrides.fetchErrors)) {
      _mockFetchError(url, msg);
    }
  }
  (globalThis as any).init();
}

// ─────────────────────────────────────────────────────────────────────────────
// init() tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('init()', () => {
  _it('should load config from store if available', () => {
    freshInit({ config: { apiId: 12345, apiHash: 'abc123' } });
    const status = _callTool('telegram-status');
    _assertEqual(status.hasCredentials, true, 'should have credentials');
  });

  _it('should load API ID from environment', () => {
    freshInit({ env: { TELEGRAM_API_ID: '98765', TELEGRAM_API_HASH: 'xyz789' } });
    const status = _callTool('telegram-status');
    _assertEqual(status.hasCredentials, true, 'should have credentials from env');
  });

  _it('should not have credentials when not configured', () => {
    freshInit();
    const status = _callTool('telegram-status');
    _assertEqual(status.hasCredentials, false, 'should not have credentials');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// telegram-ping tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('telegram-ping', () => {
  _it('should return success when telegram.org is reachable', () => {
    freshInit({
      fetchResponses: {
        'https://telegram.org': { status: 200, body: '' },
        'https://api.telegram.org': { status: 200, body: '' },
        'https://core.telegram.org': { status: 200, body: '' },
      },
    });
    const result = _callTool('telegram-ping');
    _assertEqual(result.success, true, 'should be successful');
    _assertContains(result.message, 'reachable', 'message should indicate reachable');
    _assertNotNull(result.avg_latency_ms, 'should have average latency');
    _assertEqual(result.endpoints.length, 3, 'should have 3 endpoint results');
  });

  _it('should return failure when all endpoints are unreachable', () => {
    freshInit({
      fetchErrors: {
        'https://telegram.org': 'Connection refused',
        'https://api.telegram.org': 'Connection refused',
        'https://core.telegram.org': 'Connection refused',
      },
    });
    const result = _callTool('telegram-ping');
    _assertEqual(result.success, false, 'should be unsuccessful');
    _assertContains(result.message, 'Unable', 'message should indicate failure');
    _assertEqual(result.avg_latency_ms, null, 'should have no average latency');
  });

  _it('should return partial success when some endpoints are reachable', () => {
    freshInit({
      fetchResponses: { 'https://telegram.org': { status: 200, body: '' } },
      fetchErrors: {
        'https://api.telegram.org': 'Connection refused',
        'https://core.telegram.org': 'Connection refused',
      },
    });
    const result = _callTool('telegram-ping');
    _assertEqual(result.success, true, 'should be successful with partial connectivity');
    const successCount = result.endpoints.filter((e: any) => e.success).length;
    _assertEqual(successCount, 1, 'should have 1 successful endpoint');
  });

  _it('should handle non-2xx status codes as failure', () => {
    freshInit({
      fetchResponses: {
        'https://telegram.org': { status: 500, body: 'Internal Server Error' },
        'https://api.telegram.org': { status: 503, body: 'Service Unavailable' },
        'https://core.telegram.org': { status: 404, body: 'Not Found' },
      },
    });
    const result = _callTool('telegram-ping');
    _assertEqual(result.success, false, 'should be unsuccessful with non-2xx status');
    const successCount = result.endpoints.filter((e: any) => e.success).length;
    _assertEqual(successCount, 0, 'should have no successful endpoints');
  });

  _it('should include credentials status in response', () => {
    freshInit({
      config: { apiId: 12345, apiHash: 'abc123' },
      fetchResponses: {
        'https://telegram.org': { status: 200, body: '' },
        'https://api.telegram.org': { status: 200, body: '' },
        'https://core.telegram.org': { status: 200, body: '' },
      },
    });
    const result = _callTool('telegram-ping');
    _assertEqual(result.has_credentials, true, 'should indicate credentials are configured');
    _assertEqual(result.is_authenticated, false, 'should indicate not authenticated');
  });

  _it('should include latency for each successful endpoint', () => {
    freshInit({
      fetchResponses: {
        'https://telegram.org': { status: 200, body: '' },
        'https://api.telegram.org': { status: 200, body: '' },
        'https://core.telegram.org': { status: 200, body: '' },
      },
    });
    const result = _callTool('telegram-ping');
    for (const endpoint of result.endpoints) {
      if (endpoint.success) {
        _assertNotNull(endpoint.latency_ms, `${endpoint.endpoint} should have latency`);
        _assertGreaterThan(endpoint.latency_ms, -1, 'latency should be non-negative');
      }
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// telegram-status tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('telegram-status', () => {
  _it('should return status object', () => {
    freshInit();
    const status = _callTool('telegram-status');
    _assertNotNull(status, 'should return status');
    _assertEqual(status.connected, false, 'should not be connected');
    _assertEqual(status.hasCredentials, false, 'should not have credentials');
    _assertNotNull(status.authState, 'should have auth state');
  });

  _it('should show hasCredentials true when configured', () => {
    freshInit({ config: { apiId: 12345, apiHash: 'abc123' } });
    const status = _callTool('telegram-status');
    _assertEqual(status.hasCredentials, true, 'should have credentials');
  });

  _it('should mask phone number', () => {
    freshInit({ config: { phoneNumber: '+15551234567' } });
    const status = _callTool('telegram-status');
    _assertContains(status.phoneNumber, '+155', 'should show first 4 digits');
    _assertContains(status.phoneNumber, '****', 'should mask rest of number');
  });
});
