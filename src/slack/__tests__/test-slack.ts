// test-slack.ts — Tests for the Slack skill.
// Run with the V8/Deno test harness when available.

const _describe = (globalThis as Record<string, unknown>).describe as (name: string, fn: () => void) => void;
const _it = (globalThis as Record<string, unknown>).it as (name: string, fn: () => void) => void;
const _assertEqual = (globalThis as Record<string, unknown>).assertEqual as (
  a: unknown,
  b: unknown,
  msg?: string
) => void;
const _assert = (globalThis as Record<string, unknown>).assert as (cond: unknown, msg?: string) => void;
const _setup = (globalThis as Record<string, unknown>).setupSkillTest as (opts?: {
  storeData?: Record<string, unknown>;
  fetchResponses?: Record<string, { status: number; body: string }>;
}) => void;
const _callTool = (globalThis as Record<string, unknown>).callTool as (
  name: string,
  args?: Record<string, unknown>
) => unknown;

function freshInit(overrides?: {
  config?: { botToken?: string; workspaceName?: string };
  fetchResponses?: Record<string, { status: number; body: string }>;
}): void {
  _setup({
    storeData: { config: { botToken: 'xoxb-test', workspaceName: 'Test', ...overrides?.config } },
    fetchResponses: {
      'https://slack.com/api/auth.test': { status: 200, body: '{"ok":true,"team":"Test"}' },
      'https://slack.com/api/conversations.list': {
        status: 200,
        body: '{"ok":true,"channels":[{"id":"C123","name":"general","is_private":false}]}',
      },
      'https://slack.com/api/conversations.history': {
        status: 200,
        body: '{"ok":true,"messages":[{"ts":"123.0","user":"U1","text":"Hello"}]}',
      },
      'https://slack.com/api/chat.postMessage': {
        status: 200,
        body: '{"ok":true,"ts":"124.0","channel":"C123","message":{"ts":"124.0","channel":"C123","text":"Hi"}}',
      },
      ...overrides?.fetchResponses,
    },
  });
  const skill = (globalThis as Record<string, unknown>).__skill?.default as { init: () => void };
  if (skill?.init) skill.init();
}

_describe('Slack skill', () => {
  _it('should return error when not connected', () => {
    _setup({ storeData: {} });
    const skill = (globalThis as Record<string, unknown>).__skill?.default as { init: () => void };
    if (skill?.init) skill.init();
    const result = _callTool('list_channels', {}) as Record<string, unknown>;
    const parsed = typeof result === 'string' ? JSON.parse(result as string) : result;
    _assertEqual(parsed.ok, false, 'should not be ok when not connected');
    _assert(
      String(parsed.error || '').toLowerCase().includes('connect'),
      'error should mention connection'
    );
  });

  _it('should list channels when connected', () => {
    freshInit();
    const result = _callTool('list_channels', {}) as string | Record<string, unknown>;
    const parsed = typeof result === 'string' ? JSON.parse(result) : result;
    _assertEqual(parsed.ok, true, 'should be ok');
    _assert(Array.isArray(parsed.channels), 'channels should be array');
  });

  _it('should get messages when connected', () => {
    freshInit();
    const result = _callTool('get_messages', { channel_id: 'C123' }) as string | Record<string, unknown>;
    const parsed = typeof result === 'string' ? JSON.parse(result) : result;
    _assertEqual(parsed.ok, true, 'should be ok');
    _assert(Array.isArray(parsed.messages), 'messages should be array');
  });

  _it('should send message when connected', () => {
    freshInit();
    const result = _callTool('send_message', { channel_id: 'C123', text: 'Hi' }) as string | Record<string, unknown>;
    const parsed = typeof result === 'string' ? JSON.parse(result) : result;
    _assertEqual(parsed.ok, true, 'should be ok');
  });

  _it('should return stored messages from DB', () => {
    freshInit();
    const result = _callTool('get_stored_messages', { limit: 10 }) as string | Record<string, unknown>;
    const parsed = typeof result === 'string' ? JSON.parse(result) : result;
    _assertEqual(parsed.ok, true, 'should be ok');
    _assert(Array.isArray(parsed.messages), 'messages should be array');
  });
});
