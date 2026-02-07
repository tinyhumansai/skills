// test-notion.ts — Tests for the Notion skill.
// Runs via the V8 test harness.
// Includes tests for both OAuth and legacy token authentication.

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
const _setup = (globalThis as any).setupSkillTest as (opts?: any) => void;
const _callTool = (globalThis as any).callTool as (name: string, args?: any) => any;
const _getMockState = (globalThis as any).getMockState as () => any;
const _mockFetchResponse = (globalThis as any).mockFetchResponse as (
  url: string,
  status: number,
  body: string,
  headers?: Record<string, string>
) => void;

// Mock Notion API responses
const MOCK_USER_ME = { object: 'user', id: 'user-123', name: 'Test Bot', type: 'bot' };

const MOCK_PAGE = {
  object: 'page',
  id: 'page-abc-123',
  url: 'https://notion.so/Test-Page-abc123',
  created_time: '2024-01-01T00:00:00.000Z',
  last_edited_time: '2024-01-02T00:00:00.000Z',
  archived: false,
  parent: { type: 'workspace' },
  properties: { title: { type: 'title', title: [{ plain_text: 'Test Page' }] } },
};

const MOCK_DATABASE = {
  object: 'database',
  id: 'db-xyz-789',
  url: 'https://notion.so/Test-Database-xyz789',
  created_time: '2024-01-01T00:00:00.000Z',
  last_edited_time: '2024-01-02T00:00:00.000Z',
  title: [{ plain_text: 'Test Database' }],
  properties: {
    Name: { id: 'title', type: 'title', title: {} },
    Status: {
      id: 'status',
      type: 'select',
      select: { options: [{ name: 'Todo' }, { name: 'Done' }] },
    },
  },
};

const MOCK_BLOCK = {
  object: 'block',
  id: 'block-def-456',
  type: 'paragraph',
  has_children: false,
  paragraph: { rich_text: [{ plain_text: 'Hello world' }] },
};

const MOCK_SEARCH_RESULTS = { results: [MOCK_PAGE, MOCK_DATABASE], has_more: false };

const VALID_TOKEN = 'ntn_test_token_12345';

// Mock OAuth credentials
const MOCK_OAUTH_CREDENTIALS = {
  accessToken: 'ntn_oauth_token_xyz',
  tokenType: 'bearer',
  workspaceId: 'ws-123',
  workspaceName: 'OAuth Workspace',
  botId: 'bot-456',
};

// ---------------------------------------------------------------------------
// Setup helpers
// ---------------------------------------------------------------------------

/** Reset mocks and re-init with clean defaults (no OAuth) */
function freshInit(overrides?: {
  config?: Record<string, unknown>;
  fetchResponses?: Record<
    string,
    { status: number; headers?: Record<string, string>; body: string }
  >;
  oauthAvailable?: boolean;
  oauthCredentials?: Record<string, unknown> | null;
}): void {
  const storeData: Record<string, unknown> = { config: overrides?.config || {} };

  _setup({
    storeData,
    fetchResponses: overrides?.fetchResponses || {},
    // OAuth mock configuration
    oauthAvailable: overrides?.oauthAvailable ?? false,
    oauthCredentials: overrides?.oauthCredentials ?? null,
  });

  // Reset skill module-level state
  (globalThis as any).CONFIG = { token: '', workspaceName: '', workspaceId: '', authMethod: '' };
  (globalThis as any).init();
}

/** Configure with valid legacy token and mock successful API calls */
function configuredInitWithToken(
  additionalFetchResponses?: Record<string, { status: number; body: string }>
): void {
  const fetchResponses: Record<string, { status: number; body: string }> = {
    'https://api.notion.com/v1/users/me': { status: 200, body: JSON.stringify(MOCK_USER_ME) },
    'https://api.notion.com/v1/search': { status: 200, body: JSON.stringify(MOCK_SEARCH_RESULTS) },
    ...additionalFetchResponses,
  };

  freshInit({
    config: { token: VALID_TOKEN, workspaceName: 'Test Workspace', authMethod: 'token' },
    fetchResponses,
    oauthAvailable: false,
  });
}

/** Configure with OAuth credentials and mock successful API calls */
function configuredInitWithOAuth(
  additionalFetchResponses?: Record<string, { status: number; body: string }>
): void {
  const fetchResponses: Record<string, { status: number; body: string }> = {
    'https://api.notion.com/v1/users/me': { status: 200, body: JSON.stringify(MOCK_USER_ME) },
    'https://api.notion.com/v1/search': { status: 200, body: JSON.stringify(MOCK_SEARCH_RESULTS) },
    ...additionalFetchResponses,
  };

  freshInit({
    config: { workspaceName: 'OAuth Workspace', workspaceId: 'ws-123', authMethod: 'oauth' },
    fetchResponses,
    oauthAvailable: true,
    oauthCredentials: { notion: MOCK_OAUTH_CREDENTIALS },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// init() tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('init()', () => {
  _it('should load legacy token config from store if available', () => {
    freshInit({
      config: { token: VALID_TOKEN, workspaceName: 'My Workspace', authMethod: 'token' },
    });
    const mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true, 'should be connected');
    _assertEqual(mock.stateValues['workspaceName'], 'My Workspace');
    _assertEqual(mock.stateValues['authMethod'], 'token');
  });

  _it('should detect OAuth credentials on init', () => {
    freshInit({
      config: { workspaceName: '', authMethod: '' },
      oauthAvailable: true,
      oauthCredentials: { notion: MOCK_OAUTH_CREDENTIALS },
    });
    const mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true, 'should be connected via OAuth');
    _assertEqual(mock.stateValues['authMethod'], 'oauth');
  });

  _it('should handle missing config gracefully', () => {
    freshInit();
    const _mock = _getMockState();
    // State may not be published yet without start()
    // Just ensure no errors
    _assert(true, 'should initialize without errors');
  });

  _it('should prefer OAuth over legacy token when both available', () => {
    freshInit({
      config: { token: VALID_TOKEN, workspaceName: 'Token Workspace', authMethod: 'token' },
      oauthAvailable: true,
      oauthCredentials: { notion: MOCK_OAUTH_CREDENTIALS },
    });
    const mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true);
    _assertEqual(mock.stateValues['authMethod'], 'oauth', 'should prefer OAuth');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// start() tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('start()', () => {
  _it('should publish connected state when configured with token', () => {
    configuredInitWithToken();
    (globalThis as any).start();
    const mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true);
  });

  _it('should publish connected state when configured with OAuth', () => {
    configuredInitWithOAuth();
    (globalThis as any).start();
    const mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true);
    _assertEqual(mock.stateValues['authMethod'], 'oauth');
  });

  _it('should not fail when not configured', () => {
    freshInit();
    (globalThis as any).start();
    _assert(true, 'should start without errors');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Setup flow tests - Legacy token
// ─────────────────────────────────────────────────────────────────────────────

_describe('Setup flow - Legacy token (no OAuth)', () => {
  _it('onSetupStart should return token step when OAuth not available', () => {
    freshInit({ oauthAvailable: false });
    const result = (globalThis as any).onSetupStart();
    _assertEqual(result.step.id, 'token', 'step id should be token');
    _assert(result.step.fields.length >= 1, 'should have at least 1 field');
    const fieldNames = result.step.fields.map((f: any) => f.name);
    _assertContains(fieldNames.join(','), 'token');
  });

  _it('onSetupSubmit should validate empty token', () => {
    freshInit({ oauthAvailable: false });
    const result = (globalThis as any).onSetupSubmit({ stepId: 'token', values: { token: '' } });
    _assertEqual(result.status, 'error', 'should return error');
    _assert(result.errors.length > 0, 'should have errors');
    _assertEqual(result.errors[0].field, 'token');
  });

  _it('onSetupSubmit should validate token format', () => {
    freshInit({ oauthAvailable: false });
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'token',
      values: { token: 'invalid_token_format' },
    });
    _assertEqual(result.status, 'error', 'should reject invalid format');
    _assertContains(result.errors[0].message, 'ntn_', 'should mention valid format');
  });

  _it('onSetupSubmit should complete with valid token', () => {
    freshInit({
      fetchResponses: {
        'https://api.notion.com/v1/users/me': { status: 200, body: JSON.stringify(MOCK_USER_ME) },
      },
      oauthAvailable: false,
    });
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'token',
      values: { token: VALID_TOKEN, workspaceName: 'My Workspace' },
    });
    _assertEqual(result.status, 'complete', 'should complete');
    const mock = _getMockState();
    _assert(mock.store['config'], 'config should be persisted');
    _assert(mock.dataFiles['config.json'], 'config.json should be written');
    _assertEqual(mock.stateValues['authMethod'], 'token');
  });

  _it('onSetupSubmit should handle unauthorized token', () => {
    freshInit({
      fetchResponses: {
        'https://api.notion.com/v1/users/me': {
          status: 401,
          body: JSON.stringify({ message: 'Invalid token' }),
        },
      },
      oauthAvailable: false,
    });
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'token',
      values: { token: VALID_TOKEN },
    });
    _assertEqual(result.status, 'error');
    _assertContains(result.errors[0].message.toLowerCase(), 'unauthorized');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Setup flow tests - OAuth
// ─────────────────────────────────────────────────────────────────────────────

_describe('Setup flow - OAuth', () => {
  _it('onSetupStart should return OAuth step when OAuth is available', () => {
    freshInit({ oauthAvailable: true });
    const result = (globalThis as any).onSetupStart();
    _assertEqual(result.step.id, 'oauth', 'step id should be oauth');
    const fieldNames = result.step.fields.map((f: any) => f.name);
    _assertContains(fieldNames.join(','), 'startOAuth');
  });

  _it('onSetupStart should show already-connected when OAuth credentials exist', () => {
    freshInit({ oauthAvailable: true, oauthCredentials: { notion: MOCK_OAUTH_CREDENTIALS } });
    const result = (globalThis as any).onSetupStart();
    _assertEqual(result.step.id, 'already-connected');
    _assertContains(result.step.description, 'OAuth Workspace');
  });

  _it('onSetupStart should show migrate step for legacy token users when OAuth available', () => {
    freshInit({
      config: { token: VALID_TOKEN, workspaceName: 'Old Workspace', authMethod: 'token' },
      oauthAvailable: true,
      oauthCredentials: null,
    });
    const result = (globalThis as any).onSetupStart();
    _assertEqual(result.step.id, 'migrate', 'should offer migration');
    _assertContains(result.step.description.toLowerCase(), 'oauth');
  });

  _it('onSetupSubmit should handle already-connected keep action', () => {
    freshInit({ oauthAvailable: true, oauthCredentials: { notion: MOCK_OAUTH_CREDENTIALS } });
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'already-connected',
      values: { action: 'keep' },
    });
    _assertEqual(result.status, 'complete');
  });

  _it('onSetupSubmit should handle already-connected reconnect action', () => {
    freshInit({ oauthAvailable: true, oauthCredentials: { notion: MOCK_OAUTH_CREDENTIALS } });
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'already-connected',
      values: { action: 'reconnect' },
    });
    _assertEqual(result.status, 'next');
    // Should have revoked credentials
    const mock = _getMockState();
    _assertEqual(mock.oauthRevoked?.notion, true, 'should revoke OAuth credentials');
  });

  _it('onSetupSubmit should handle migration keep action', () => {
    freshInit({
      config: { token: VALID_TOKEN, workspaceName: 'Old Workspace', authMethod: 'token' },
      oauthAvailable: true,
    });
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'migrate',
      values: { action: 'keep' },
    });
    _assertEqual(result.status, 'complete');
  });

  _it('onSetupSubmit should handle migration to OAuth', () => {
    freshInit({
      config: { token: VALID_TOKEN, workspaceName: 'Old Workspace', authMethod: 'token' },
      oauthAvailable: true,
    });
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'migrate',
      values: { action: 'oauth' },
    });
    _assertEqual(result.status, 'next');
    _assertEqual(result.nextStep.id, 'oauth');
  });

  _it('onSetupSubmit OAuth step should start flow when triggered', () => {
    freshInit({ oauthAvailable: true, oauthCredentials: null });
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'oauth',
      values: { startOAuth: true, workspaceLabel: 'My Label' },
    });
    _assertEqual(result.status, 'next');
    _assertEqual(result.nextStep.id, 'oauth-pending');
    // Should have flow ID from mock
    const flowIdField = result.nextStep.fields.find((f: any) => f.name === 'flowId');
    _assertNotNull(flowIdField?.default, 'should have flow ID');
  });

  _it('onSetupSubmit OAuth step should complete if credentials already exist', () => {
    freshInit({ oauthAvailable: true, oauthCredentials: { notion: MOCK_OAUTH_CREDENTIALS } });
    // Simulate user coming back after OAuth completed
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'oauth',
      values: { startOAuth: false, workspaceLabel: 'Custom Label' },
    });
    _assertEqual(result.status, 'complete');
    const mock = _getMockState();
    _assertEqual(mock.stateValues['authMethod'], 'oauth');
  });

  _it('onSetupSubmit oauth-pending should complete when flow is complete', () => {
    freshInit({ oauthAvailable: true, oauthCredentials: { notion: MOCK_OAUTH_CREDENTIALS } });
    // Mock flow status as complete
    (globalThis as any).__mockOAuthFlowStatus = { status: 'complete' };

    const result = (globalThis as any).onSetupSubmit({
      stepId: 'oauth-pending',
      values: { flowId: 'flow-123', workspaceLabel: 'My Workspace' },
    });
    _assertEqual(result.status, 'complete');
    const mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true);
    _assertEqual(mock.stateValues['authMethod'], 'oauth');
  });

  _it('onSetupSubmit oauth-pending should error when flow fails', () => {
    freshInit({ oauthAvailable: true, oauthCredentials: null });
    // Mock flow status as failed
    (globalThis as any).__mockOAuthFlowStatus = { status: 'failed', error: 'User denied access' };

    const result = (globalThis as any).onSetupSubmit({
      stepId: 'oauth-pending',
      values: { flowId: 'flow-123', workspaceLabel: '' },
    });
    _assertEqual(result.status, 'error');
    _assertContains(result.errors[0].message, 'denied');
  });

  _it('onSetupSubmit oauth-pending should error when flow expires', () => {
    freshInit({ oauthAvailable: true, oauthCredentials: null });
    (globalThis as any).__mockOAuthFlowStatus = { status: 'expired' };

    const result = (globalThis as any).onSetupSubmit({
      stepId: 'oauth-pending',
      values: { flowId: 'flow-123', workspaceLabel: '' },
    });
    _assertEqual(result.status, 'error');
    _assertContains(result.errors[0].message.toLowerCase(), 'timed out');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Disconnect tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Disconnect', () => {
  _it('onDisconnect should clear legacy token config', () => {
    configuredInitWithToken();
    (globalThis as any).start();
    let mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true);

    (globalThis as any).onDisconnect();
    mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], false);
    _assertEqual(mock.stateValues['authMethod'], null);
  });

  _it('onDisconnect should revoke OAuth credentials', () => {
    configuredInitWithOAuth();
    (globalThis as any).start();
    let mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true);

    (globalThis as any).onDisconnect();
    mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], false);
    _assertEqual(mock.oauthRevoked?.notion, true, 'should revoke OAuth credentials');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// API calls with OAuth
// ─────────────────────────────────────────────────────────────────────────────

_describe('API calls with OAuth', () => {
  _it('should use OAuth token for API calls', () => {
    configuredInitWithOAuth();
    const result = _callTool('notion-search', { query: 'test' });
    _assertNotNull(result, 'should return result');
    _assertEqual(result.count, 2, 'should have 2 results');

    // Verify Authorization header used OAuth token
    const mock = _getMockState();
    const searchCall = mock.fetchCalls.find((c: any) => c.url.includes('/search'));
    _assertContains(searchCall.headers['Authorization'], MOCK_OAUTH_CREDENTIALS.accessToken);
  });

  _it('should handle 401 by revoking OAuth credentials', () => {
    freshInit({
      config: { workspaceName: 'OAuth Workspace', authMethod: 'oauth' },
      fetchResponses: {
        'https://api.notion.com/v1/search': {
          status: 401,
          body: JSON.stringify({ message: 'Unauthorized' }),
        },
      },
      oauthAvailable: true,
      oauthCredentials: { notion: MOCK_OAUTH_CREDENTIALS },
    });

    const result = _callTool('notion-search', { query: 'test' });
    _assert(result.error, 'should return error');
    _assertContains(result.error.toLowerCase(), 'revoked');

    const mock = _getMockState();
    _assertEqual(mock.oauthRevoked?.notion, true, 'should revoke credentials on 401');
    _assertEqual(mock.stateValues['connected'], false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Search tool tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('notion-search tool', () => {
  _it('should search pages and databases', () => {
    configuredInitWithToken();
    const result = _callTool('notion-search', { query: 'test' });
    _assertNotNull(result, 'should return result');
    _assertEqual(result.count, 2, 'should have 2 results');
    _assert(Array.isArray(result.results), 'results should be array');
  });

  _it('should filter by page type', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/search': {
        status: 200,
        body: JSON.stringify({ results: [MOCK_PAGE], has_more: false }),
      },
    });
    const result = _callTool('notion-search', { filter: 'page' });
    _assertEqual(result.count, 1);
  });

  _it('should handle empty results', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/search': {
        status: 200,
        body: JSON.stringify({ results: [], has_more: false }),
      },
    });
    const result = _callTool('notion-search', { query: 'nonexistent' });
    _assertEqual(result.count, 0);
  });

  _it('should require connection', () => {
    freshInit();
    const result = _callTool('notion-search', { query: 'test' });
    _assert(result.error, 'should return error when not connected');
    _assertContains(result.error.toLowerCase(), 'not connected');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Page tools tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Page tools', () => {
  _it('notion-get-page should return page details', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/pages/page-123': { status: 200, body: JSON.stringify(MOCK_PAGE) },
    });
    const result = _callTool('notion-get-page', { page_id: 'page-123' });
    _assertNotNull(result.id);
    _assertEqual(result.title, 'Test Page');
  });

  _it('notion-get-page should require page_id', () => {
    configuredInitWithToken();
    const result = _callTool('notion-get-page', {});
    _assert(result.error, 'should return error');
    _assertContains(result.error, 'page_id');
  });

  _it('notion-create-page should create page', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/pages': { status: 200, body: JSON.stringify(MOCK_PAGE) },
    });
    const result = _callTool('notion-create-page', { parent_id: 'parent-123', title: 'New Page' });
    _assertEqual(result.success, true);
    _assertNotNull(result.page);
  });

  _it('notion-create-page should require parent_id and title', () => {
    configuredInitWithToken();
    const result1 = _callTool('notion-create-page', { title: 'Test' });
    _assert(result1.error, 'should require parent_id');

    const result2 = _callTool('notion-create-page', { parent_id: '123' });
    _assert(result2.error, 'should require title');
  });

  _it('notion-delete-page should archive page', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/pages/page-123': {
        status: 200,
        body: JSON.stringify({ ...MOCK_PAGE, archived: true }),
      },
    });
    const result = _callTool('notion-delete-page', { page_id: 'page-123' });
    _assertEqual(result.success, true);
    _assertContains(result.message.toLowerCase(), 'archived');
  });

  _it('notion-list-all-pages should return pages', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/search': {
        status: 200,
        body: JSON.stringify({ results: [MOCK_PAGE], has_more: false }),
      },
    });
    const result = _callTool('notion-list-all-pages', {});
    _assert(Array.isArray(result.pages), 'should return pages array');
    _assertEqual(result.count, 1);
  });

  _it('notion-append-text should append content', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/blocks/page-123/children': {
        status: 200,
        body: JSON.stringify({ results: [MOCK_BLOCK] }),
      },
    });
    const result = _callTool('notion-append-text', { block_id: 'page-123', text: 'Hello world' });
    _assertEqual(result.success, true);
    _assertNotNull(result.blocks_added);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Database tools tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Database tools', () => {
  _it('notion-get-database should return database schema', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/databases/db-123': {
        status: 200,
        body: JSON.stringify(MOCK_DATABASE),
      },
    });
    const result = _callTool('notion-get-database', { database_id: 'db-123' });
    _assertNotNull(result.id);
    _assertEqual(result.title, 'Test Database');
    _assertNotNull(result.schema);
  });

  _it('notion-query-database should return rows', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/databases/db-123/query': {
        status: 200,
        body: JSON.stringify({ results: [MOCK_PAGE], has_more: false }),
      },
    });
    const result = _callTool('notion-query-database', { database_id: 'db-123' });
    _assert(Array.isArray(result.rows), 'should return rows array');
    _assertEqual(result.count, 1);
  });

  _it('notion-list-all-databases should return databases', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/search': {
        status: 200,
        body: JSON.stringify({ results: [MOCK_DATABASE], has_more: false }),
      },
    });
    const result = _callTool('notion-list-all-databases', {});
    _assert(Array.isArray(result.databases), 'should return databases array');
    _assertEqual(result.count, 1);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Block tools tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Block tools', () => {
  _it('notion-get-block should return block', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/blocks/block-123': {
        status: 200,
        body: JSON.stringify(MOCK_BLOCK),
      },
    });
    const result = _callTool('notion-get-block', { block_id: 'block-123' });
    _assertNotNull(result.id);
    _assertEqual(result.type, 'paragraph');
  });

  _it('notion-get-block-children should return children', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/blocks/page-123/children?page_size=50': {
        status: 200,
        body: JSON.stringify({ results: [MOCK_BLOCK], has_more: false }),
      },
    });
    const result = _callTool('notion-get-block-children', { block_id: 'page-123' });
    _assert(Array.isArray(result.children), 'should return children array');
    _assertEqual(result.count, 1);
  });

  _it('notion-delete-block should delete block', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/blocks/block-123': { status: 200, body: JSON.stringify({}) },
    });
    const result = _callTool('notion-delete-block', { block_id: 'block-123' });
    _assertEqual(result.success, true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// User tools tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('User tools', () => {
  _it('notion-list-users should return users', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/users?page_size=20': {
        status: 200,
        body: JSON.stringify({ results: [MOCK_USER_ME], has_more: false }),
      },
    });
    const result = _callTool('notion-list-users', {});
    _assert(Array.isArray(result.users), 'should return users array');
    _assertEqual(result.count, 1);
  });

  _it('notion-get-user should return user', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/users/user-123': {
        status: 200,
        body: JSON.stringify(MOCK_USER_ME),
      },
    });
    const result = _callTool('notion-get-user', { user_id: 'user-123' });
    _assertNotNull(result.id);
    _assertEqual(result.name, 'Test Bot');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Comment tools tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Comment tools', () => {
  _it('notion-create-comment should create comment', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/comments': {
        status: 200,
        body: JSON.stringify({
          id: 'comment-123',
          discussion_id: 'disc-456',
          created_time: '2024-01-01T00:00:00.000Z',
          rich_text: [{ plain_text: 'Test comment' }],
        }),
      },
    });
    const result = _callTool('notion-create-comment', {
      page_id: 'page-123',
      text: 'Test comment',
    });
    _assertEqual(result.success, true);
    _assertNotNull(result.comment.id);
  });

  _it('notion-create-comment should require page_id or discussion_id', () => {
    configuredInitWithToken();
    const result = _callTool('notion-create-comment', { text: 'Test' });
    _assert(result.error, 'should return error');
    _assertContains(result.error, 'page_id');
  });

  _it('notion-list-comments should return comments', () => {
    configuredInitWithToken({
      'https://api.notion.com/v1/comments?block_id=page-123&page_size=20': {
        status: 200,
        body: JSON.stringify({
          results: [
            {
              id: 'comment-123',
              discussion_id: 'disc-456',
              created_time: '2024-01-01T00:00:00.000Z',
              created_by: { id: 'user-123' },
              rich_text: [{ plain_text: 'Test comment' }],
            },
          ],
          has_more: false,
        }),
      },
    });
    const result = _callTool('notion-list-comments', { block_id: 'page-123' });
    _assert(Array.isArray(result.comments), 'should return comments array');
    _assertEqual(result.count, 1);
  });
});
