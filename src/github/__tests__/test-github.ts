// test-github.ts — Tests for the GitHub skill.

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
  body: string
) => void;

const GITHUB_API = 'https://api.github.com';

const CLEAN_CONFIG = {
  token: '',
  username: '',
  enableRepoTools: true,
  enableIssueTools: true,
  enablePrTools: true,
  enableSearchTools: true,
  enableCodeTools: true,
  enableReleaseTools: false,
  enableGistTools: true,
  enableWorkflowTools: false,
  enableNotificationTools: false,
};

function freshInit(overrides?: {
  config?: Record<string, unknown>;
  fetchResponses?: Record<
    string,
    { status: number; headers?: Record<string, string>; body: string }
  >;
  env?: Record<string, string>;
}): void {
  const stateData: Record<string, unknown> = {
    config: { ...CLEAN_CONFIG, ...(overrides?.config || {}) },
  };
  _setup({ stateData, env: overrides?.env || {}, fetchResponses: overrides?.fetchResponses || {} });
  (globalThis as any).init();
}

// ---------------------------------------------------------------------------
// Init / State
// ---------------------------------------------------------------------------

_describe('GitHub Skill - Init', () => {
  _it('should initialize with default config', () => {
    freshInit();
    const s = (globalThis as any).getGitHubSkillState();
    _assertNotNull(s, 'Skill state should exist');
    _assertEqual(s.config.token, '', 'Token should be empty by default');
    _assertEqual(s.authenticated, false, 'Should not be authenticated');
  });

  _it('should load saved config from state', () => {
    freshInit({ config: { token: 'ghp_test123', username: 'testuser' } });
    const s = (globalThis as any).getGitHubSkillState();
    _assertEqual(s.config.token, 'ghp_test123', 'Token should be loaded');
    _assertEqual(s.config.username, 'testuser', 'Username should be loaded');
  });

  _it('should use GITHUB_TOKEN from environment', () => {
    freshInit({ env: { GITHUB_TOKEN: 'ghp_env_token' } });
    const s = (globalThis as any).getGitHubSkillState();
    _assertEqual(s.config.token, 'ghp_env_token', 'Should use env token');
  });
});

// ---------------------------------------------------------------------------
// Setup Flow
// ---------------------------------------------------------------------------

_describe('GitHub Skill - Setup', () => {
  _it('should return token step when no token configured', () => {
    freshInit();
    const result = (globalThis as any).onSetupStart();
    _assertNotNull(result.step, 'Should return a step');
    _assertEqual(result.step.id, 'token', 'Step should be token entry');
    _assert(result.step.fields.length > 0, 'Should have fields');
  });

  _it('should validate empty token on submit', () => {
    freshInit();
    const result = (globalThis as any).onSetupSubmit({ stepId: 'token', values: { token: '' } });
    _assertEqual(result.status, 'error', 'Should return error status');
    _assert(result.errors.length > 0, 'Should have errors');
  });

  _it('should validate token format on submit', () => {
    freshInit();
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'token',
      values: { token: 'invalid_token' },
    });
    _assertEqual(result.status, 'error', 'Should return error for bad format');
  });
});

// ---------------------------------------------------------------------------
// Tools - Repo
// ---------------------------------------------------------------------------

_describe('GitHub Skill - Repo Tools', () => {
  _it('should list repos', () => {
    freshInit({
      config: { token: 'ghp_test123', username: 'testuser' },
      fetchResponses: {
        [`${GITHUB_API}/user/repos?sort=updated&per_page=30`]: {
          status: 200,
          body: JSON.stringify([
            {
              full_name: 'user/repo1',
              private: false,
              stargazers_count: 10,
              language: 'TypeScript',
              description: 'Test repo',
            },
            {
              full_name: 'user/repo2',
              private: true,
              stargazers_count: 5,
              language: 'Python',
              description: 'Another repo',
            },
          ]),
        },
      },
    });
    const result = _callTool('list-repos', {});
    const parsed = JSON.parse(result);
    _assertNotNull(parsed.repos, 'Should return repos');
    _assertContains(parsed.repos, 'user/repo1', 'Should contain repo1');
  });

  _it('should get repo details', () => {
    freshInit({
      config: { token: 'ghp_test123', username: 'testuser' },
      fetchResponses: {
        [`${GITHUB_API}/repos/owner/repo`]: {
          status: 200,
          body: JSON.stringify({
            full_name: 'owner/repo',
            html_url: 'https://github.com/owner/repo',
            private: false,
            description: 'A test repo',
            stargazers_count: 42,
            forks_count: 5,
            open_issues_count: 3,
            language: 'TypeScript',
            default_branch: 'main',
            license: { name: 'MIT' },
            archived: false,
            fork: false,
            created_at: '2024-01-01',
            updated_at: '2024-06-01',
            topics: ['testing'],
          }),
        },
      },
    });
    const result = _callTool('get-repo', { owner: 'owner', repo: 'repo' });
    const parsed = JSON.parse(result);
    _assertContains(parsed.info, 'owner/repo', 'Should contain repo name');
    _assertContains(parsed.info, 'TypeScript', 'Should contain language');
  });
});

// ---------------------------------------------------------------------------
// Tools - Issues
// ---------------------------------------------------------------------------

_describe('GitHub Skill - Issue Tools', () => {
  _it('should list issues', () => {
    freshInit({
      config: { token: 'ghp_test123', username: 'testuser' },
      fetchResponses: {
        [`${GITHUB_API}/repos/owner/repo/issues?state=open&per_page=30`]: {
          status: 200,
          body: JSON.stringify([
            {
              number: 1,
              title: 'Bug report',
              state: 'open',
              user: { login: 'user1' },
              labels: [{ name: 'bug' }],
            },
            {
              number: 2,
              title: 'Feature request',
              state: 'open',
              user: { login: 'user2' },
              labels: [],
            },
          ]),
        },
      },
    });
    const result = _callTool('list-issues', { owner: 'owner', repo: 'repo' });
    const parsed = JSON.parse(result);
    _assertNotNull(parsed.issues, 'Should return issues');
    _assertContains(parsed.issues, 'Bug report', 'Should contain issue title');
  });
});

// ---------------------------------------------------------------------------
// Tools - PRs
// ---------------------------------------------------------------------------

_describe('GitHub Skill - PR Tools', () => {
  _it('should list pull requests', () => {
    freshInit({
      config: { token: 'ghp_test123', username: 'testuser' },
      fetchResponses: {
        [`${GITHUB_API}/repos/owner/repo/pulls?state=open&per_page=30`]: {
          status: 200,
          body: JSON.stringify([
            {
              number: 1,
              title: 'Add feature',
              state: 'open',
              draft: false,
              user: { login: 'dev1' },
              head: { ref: 'feature' },
              base: { ref: 'main' },
              labels: [],
            },
          ]),
        },
      },
    });
    const result = _callTool('list-prs', { owner: 'owner', repo: 'repo' });
    const parsed = JSON.parse(result);
    _assertNotNull(parsed.prs, 'Should return PRs');
    _assertContains(parsed.prs, 'Add feature', 'Should contain PR title');
  });
});

// ---------------------------------------------------------------------------
// Options
// ---------------------------------------------------------------------------

_describe('GitHub Skill - Options', () => {
  _it('should list all options', () => {
    freshInit();
    const result = (globalThis as any).onListOptions();
    _assertNotNull(result.options, 'Should return options');
    _assert(result.options.length === 9, 'Should have 9 category options');
  });

  _it('should set an option', () => {
    freshInit();
    (globalThis as any).onSetOption({ name: 'enableReleaseTools', value: true });
    const s = (globalThis as any).getGitHubSkillState();
    _assertEqual(s.config.enableReleaseTools, true, 'Release tools should be enabled');
  });
});
