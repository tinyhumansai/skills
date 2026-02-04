// test-notion.ts — Tests for the Notion skill.
// Runs via the V8 test harness.

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

/** Reset mocks and re-init with clean defaults */
function freshInit(overrides?: {
  config?: Record<string, unknown>;
  fetchResponses?: Record<
    string,
    { status: number; headers?: Record<string, string>; body: string }
  >;
}): void {
  const storeData: Record<string, unknown> = { config: overrides?.config || {} };
  _setup({ storeData, fetchResponses: overrides?.fetchResponses || {} });
  // Reset skill module-level state
  (globalThis as any).CONFIG = { token: '', workspaceName: '' };
  (globalThis as any).init();
}

/** Configure with valid token and mock successful API calls */
function configuredInit(
  additionalFetchResponses?: Record<string, { status: number; body: string }>
): void {
  const fetchResponses: Record<string, { status: number; body: string }> = {
    'https://api.notion.com/v1/users/me': { status: 200, body: JSON.stringify(MOCK_USER_ME) },
    'https://api.notion.com/v1/search': { status: 200, body: JSON.stringify(MOCK_SEARCH_RESULTS) },
    ...additionalFetchResponses,
  };

  freshInit({ config: { token: VALID_TOKEN, workspaceName: 'Test Workspace' }, fetchResponses });
}

// ─────────────────────────────────────────────────────────────────────────────
// init() tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('init()', () => {
  _it('should load config from store if available', () => {
    freshInit({ config: { token: VALID_TOKEN, workspaceName: 'My Workspace' } });
    const mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true, 'should be connected');
    _assertEqual(mock.stateValues['workspaceName'], 'My Workspace');
  });

  _it('should handle missing config gracefully', () => {
    freshInit();
    const mock = _getMockState();
    // State may not be published yet without start()
    // Just ensure no errors
    _assert(true, 'should initialize without errors');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// start() tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('start()', () => {
  _it('should publish connected state when configured', () => {
    configuredInit();
    (globalThis as any).start();
    const mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true);
  });

  _it('should not fail when not configured', () => {
    freshInit();
    (globalThis as any).start();
    // Should not throw
    _assert(true, 'should start without errors');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Setup flow tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Setup flow', () => {
  _it('onSetupStart should return token step', () => {
    freshInit();
    const result = (globalThis as any).onSetupStart();
    _assertEqual(result.step.id, 'token', 'step id');
    _assert(result.step.fields.length >= 1, 'should have at least 1 field');
    const fieldNames = result.step.fields.map((f: any) => f.name);
    _assertContains(fieldNames.join(','), 'token');
  });

  _it('onSetupSubmit should validate empty token', () => {
    freshInit();
    const result = (globalThis as any).onSetupSubmit({ stepId: 'token', values: { token: '' } });
    _assertEqual(result.status, 'error', 'should return error');
    _assert(result.errors.length > 0, 'should have errors');
    _assertEqual(result.errors[0].field, 'token');
  });

  _it('onSetupSubmit should validate token format', () => {
    freshInit();
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
    });
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'token',
      values: { token: VALID_TOKEN, workspaceName: 'My Workspace' },
    });
    _assertEqual(result.status, 'complete', 'should complete');
    const mock = _getMockState();
    _assert(mock.store['config'], 'config should be persisted');
    _assert(mock.dataFiles['config.json'], 'config.json should be written');
  });

  _it('onSetupSubmit should handle unauthorized token', () => {
    freshInit({
      fetchResponses: {
        'https://api.notion.com/v1/users/me': {
          status: 401,
          body: JSON.stringify({ message: 'Invalid token' }),
        },
      },
    });
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'token',
      values: { token: VALID_TOKEN },
    });
    _assertEqual(result.status, 'error');
    _assertContains(result.errors[0].message.toLowerCase(), 'unauthorized');
  });

  _it('onSetupSubmit should error on unknown step', () => {
    freshInit();
    const result = (globalThis as any).onSetupSubmit({ stepId: 'nonexistent', values: {} });
    _assertEqual(result.status, 'error');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Search tool tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('notion-search tool', () => {
  _it('should search pages and databases', () => {
    configuredInit();
    const result = _callTool('notion-search', { query: 'test' });
    _assertNotNull(result, 'should return result');
    _assertEqual(result.count, 2, 'should have 2 results');
    _assert(Array.isArray(result.results), 'results should be array');
  });

  _it('should filter by page type', () => {
    configuredInit({
      'https://api.notion.com/v1/search': {
        status: 200,
        body: JSON.stringify({ results: [MOCK_PAGE], has_more: false }),
      },
    });
    const result = _callTool('notion-search', { filter: 'page' });
    _assertEqual(result.count, 1);
  });

  _it('should handle empty results', () => {
    configuredInit({
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
    configuredInit({
      'https://api.notion.com/v1/pages/page-123': { status: 200, body: JSON.stringify(MOCK_PAGE) },
    });
    const result = _callTool('notion-get-page', { page_id: 'page-123' });
    _assertNotNull(result.id);
    _assertEqual(result.title, 'Test Page');
  });

  _it('notion-get-page should require page_id', () => {
    configuredInit();
    const result = _callTool('notion-get-page', {});
    _assert(result.error, 'should return error');
    _assertContains(result.error, 'page_id');
  });

  _it('notion-create-page should create page', () => {
    configuredInit({
      'https://api.notion.com/v1/pages': { status: 200, body: JSON.stringify(MOCK_PAGE) },
    });
    const result = _callTool('notion-create-page', { parent_id: 'parent-123', title: 'New Page' });
    _assertEqual(result.success, true);
    _assertNotNull(result.page);
  });

  _it('notion-create-page should require parent_id and title', () => {
    configuredInit();
    const result1 = _callTool('notion-create-page', { title: 'Test' });
    _assert(result1.error, 'should require parent_id');

    const result2 = _callTool('notion-create-page', { parent_id: '123' });
    _assert(result2.error, 'should require title');
  });

  _it('notion-delete-page should archive page', () => {
    configuredInit({
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
    configuredInit({
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
    configuredInit({
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
    configuredInit({
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
    configuredInit({
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
    configuredInit({
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
    configuredInit({
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
    configuredInit({
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
    configuredInit({
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
    configuredInit({
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
    configuredInit({
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
    configuredInit({
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
    configuredInit();
    const result = _callTool('notion-create-comment', { text: 'Test' });
    _assert(result.error, 'should return error');
    _assertContains(result.error, 'page_id');
  });

  _it('notion-list-comments should return comments', () => {
    configuredInit({
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

// ─────────────────────────────────────────────────────────────────────────────
// Disconnect tests
// ─────────────────────────────────────────────────────────────────────────────

_describe('Disconnect', () => {
  _it('onDisconnect should clear config', () => {
    configuredInit();
    (globalThis as any).start();
    let mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], true);

    (globalThis as any).onDisconnect();
    mock = _getMockState();
    _assertEqual(mock.stateValues['connected'], false);
  });
});
