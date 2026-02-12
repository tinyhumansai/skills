// GitHub skill — TypeScript implementation for QuickJS runtime
// 72 tools for repos, issues, PRs, releases, gists, actions, search, notifications, and raw API.
// Authentication via GitHub App (Device Flow).
import { checkAuth } from './api';
import './state';
import type { GitHubSkillState } from './state';
import {
  actionsTools,
  apiTools,
  codeTools,
  gistTools,
  issueTools,
  notificationTools,
  prTools,
  releaseTools,
  repoTools,
  searchTools,
} from './tools';
import type { GitHubConfig } from './types';

function getSkillState(): GitHubSkillState {
  return (
    globalThis as unknown as { getGitHubSkillState: () => GitHubSkillState }
  ).getGitHubSkillState();
}

// ---------------------------------------------------------------------------
// Lifecycle hooks
// ---------------------------------------------------------------------------

async function init(): Promise<void> {
  console.log('[github] Initializing');
  const s = getSkillState();

  // Load persisted config
  const saved = state.get('config') as Partial<GitHubConfig> | null;
  if (saved) {
    s.config.token = saved.token ?? s.config.token;
    s.config.username = saved.username ?? s.config.username;
    s.config.refreshToken = saved.refreshToken ?? s.config.refreshToken;
    s.config.tokenExpiresAt = saved.tokenExpiresAt ?? s.config.tokenExpiresAt;
    s.config.refreshTokenExpiresAt = saved.refreshTokenExpiresAt ?? s.config.refreshTokenExpiresAt;
    s.config.clientId = saved.clientId ?? s.config.clientId;
    s.config.enableRepoTools = saved.enableRepoTools ?? s.config.enableRepoTools;
    s.config.enableIssueTools = saved.enableIssueTools ?? s.config.enableIssueTools;
    s.config.enablePrTools = saved.enablePrTools ?? s.config.enablePrTools;
    s.config.enableSearchTools = saved.enableSearchTools ?? s.config.enableSearchTools;
    s.config.enableCodeTools = saved.enableCodeTools ?? s.config.enableCodeTools;
    s.config.enableReleaseTools = saved.enableReleaseTools ?? s.config.enableReleaseTools;
    s.config.enableGistTools = saved.enableGistTools ?? s.config.enableGistTools;
    s.config.enableWorkflowTools = saved.enableWorkflowTools ?? s.config.enableWorkflowTools;
    s.config.enableNotificationTools =
      saved.enableNotificationTools ?? s.config.enableNotificationTools;
  }

  // Fallback: use GITHUB_TOKEN from environment (e.g. REPL or when state is from another process)
  if (!s.config.token) {
    const envToken = platform.env('GITHUB_TOKEN');
    if (envToken) s.config.token = envToken;
  }

  console.log(`[github] Config loaded — user: ${s.config.username || '(not authenticated)'}`);
}

async function start(): Promise<void> {
  const s = getSkillState();

  if (!s.config.token) {
    console.warn('[github] No token configured — waiting for setup');
    publishState();
    return;
  }

  // Auto-refresh token if needed before verifying
  await globalThis.githubOAuth.ensureValidToken();

  // Verify authentication
  const auth = await checkAuth();
  s.authenticated = auth.authenticated;
  if (auth.authenticated) {
    s.config.username = auth.username;
    console.log(`[github] Authenticated as @${auth.username}`);
  } else {
    console.error('[github] Authentication failed');
  }

  // Register notification check cron (every 5 minutes)
  cron.register('github-notifications', '0 */5 * * * *');

  publishState();
}

async function stop(): Promise<void> {
  console.log('[github] Stopping');
  const s = getSkillState();

  cron.unregister('github-notifications');

  // Persist config
  state.set('config', s.config);
}

// ---------------------------------------------------------------------------
// Cron handler
// ---------------------------------------------------------------------------

async function onCronTrigger(scheduleId: string): Promise<void> {
  if (scheduleId === 'github-notifications') {
    await checkNotifications();
  }
}

async function checkNotifications(): Promise<void> {
  const s = getSkillState();
  if (!s.authenticated) return;

  try {
    // Auto-refresh before making the call
    await globalThis.githubOAuth.ensureValidToken();

    const response = await net.fetch('https://api.github.com/notifications?per_page=1', {
      method: 'GET',
      headers: { Authorization: `Bearer ${s.config.token}`, Accept: 'application/vnd.github+json' },
      timeout: 10000,
    });

    if (response.status === 200) {
      const notifications = JSON.parse(response.body) as unknown[];
      if (notifications.length > 0) {
        console.log('[github] Unread notifications available');
      }
    }
  } catch (e) {
    console.warn(`[github] Notification check failed: ${e}`);
  }
}

// ---------------------------------------------------------------------------
// Setup flow (GitHub App — Device Flow)
// ---------------------------------------------------------------------------

async function onSetupStart(): Promise<SetupStartResult> {
  console.log('[github] onSetupStart');
  const s = getSkillState();

  // Check existing config — auto-refresh if needed
  if (s.config.token) {
    await globalThis.githubOAuth.ensureValidToken();
    const auth = await checkAuth();
    if (auth.authenticated) {
      s.config.username = auth.username;
      s.authenticated = true;
      state.set('config', s.config);
      publishState();
      return {
        step: {
          id: 'existing-complete',
          title: 'Already Connected',
          description: `Already connected as @${auth.username} via GitHub App.`,
          fields: [],
        },
      };
    }
  }

  // Verify client ID is available
  const clientId = platform.env('GITHUB_APP_CLIENT_ID') ?? '';
  if (!clientId) {
    return {
      step: {
        id: 'missing-config',
        title: 'GitHub App Not Configured',
        description:
          'The GITHUB_APP_CLIENT_ID environment variable is not set. Please configure the GitHub App credentials before connecting.',
        fields: [],
      },
    };
  }

  // Start device flow directly
  try {
    const deviceCode = await globalThis.githubOAuth.requestDeviceCode(clientId);

    console.log(
      `[github] Device flow started — user code: ${deviceCode.user_code}, verify at: ${deviceCode.verification_uri}`
    );

    // Store device_code in transient state for polling
    (s as unknown as Record<string, unknown>).__deviceCode = deviceCode.device_code;
    (s as unknown as Record<string, unknown>).__deviceInterval = deviceCode.interval;
    (s as unknown as Record<string, unknown>).__deviceClientId = clientId;
    (s as unknown as Record<string, unknown>).__deviceExpiresAt =
      Date.now() + deviceCode.expires_in * 1000;

    return {
      step: {
        id: 'device-code',
        title: 'Authorize AlphaHuman',
        description: `Open ${deviceCode.verification_uri} in your browser and enter this code:\n\n**${deviceCode.user_code}**\n\nOnce you have authorized the app on GitHub, click Continue below.`,
        fields: [
          {
            name: 'verification_uri',
            type: 'text',
            label: 'Verification URL',
            description: 'Used by REPL to open in browser (optional)',
            required: false,
            default: deviceCode.verification_uri,
          },
          {
            name: 'ready',
            type: 'boolean',
            label: "I've authorized on GitHub",
            description: 'Press Enter after you have entered the code and authorized the app.',
            required: false,
            default: true,
          },
          {
            name: 'user_code',
            type: 'text',
            label: 'Your Code (for reference)',
            description: 'This is your verification code — enter it on GitHub',
            required: false,
            default: deviceCode.user_code,
          },
        ],
      },
    };
  } catch (e) {
    return {
      step: {
        id: 'error',
        title: 'Connection Failed',
        description: `Failed to start GitHub App authorization: ${e}`,
        fields: [],
      },
    };
  }
}

async function onSetupSubmit(args: {
  stepId: string;
  values: Record<string, unknown>;
}): Promise<SetupSubmitResult> {
  const { stepId } = args;

  if (stepId === 'existing-complete') {
    return { status: 'complete' };
  }

  if (stepId === 'missing-config' || stepId === 'error') {
    return {
      status: 'error',
      errors: [
        { field: '', message: 'Setup cannot proceed. Fix the configuration and try again.' },
      ],
    };
  }

  // ---------------------------------------------------------------------------
  // Step: device-code — user has authorized on GitHub, now we poll for token
  // ---------------------------------------------------------------------------
  if (stepId === 'device-code') {
    return handleDeviceCodePoll();
  }

  return { status: 'error', errors: [{ field: '', message: `Unknown step: ${stepId}` }] };
}

// ---------------------------------------------------------------------------
// GitHub App Device Flow — poll for token
// ---------------------------------------------------------------------------
async function handleDeviceCodePoll(): Promise<SetupSubmitResult> {
  const s = getSkillState();
  const deviceCode = (s as unknown as Record<string, unknown>).__deviceCode as string;
  const clientId = (s as unknown as Record<string, unknown>).__deviceClientId as string;
  const expiresAt = (s as unknown as Record<string, unknown>).__deviceExpiresAt as number;

  if (!deviceCode || !clientId) {
    return {
      status: 'error',
      errors: [{ field: '', message: 'Device flow session expired. Please start over.' }],
    };
  }

  if (Date.now() >= expiresAt) {
    return {
      status: 'error',
      errors: [{ field: '', message: 'Authorization code expired. Please start setup again.' }],
    };
  }

  // Poll up to 12 times (about 60 seconds with 5-second intervals)
  const maxAttempts = 12;
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const result = await globalThis.githubOAuth.pollForAccessToken(clientId, deviceCode);

      // Check if it's an error response
      if ('error' in result && result.error) {
        if (result.error === 'authorization_pending') {
          continue;
        }
        if (result.error === 'slow_down') {
          continue;
        }
        if (result.error === 'expired_token') {
          return {
            status: 'error',
            errors: [
              { field: '', message: 'Authorization code expired. Please start setup again.' },
            ],
          };
        }
        if (result.error === 'access_denied') {
          return {
            status: 'error',
            errors: [{ field: '', message: 'Authorization was denied. Please try again.' }],
          };
        }
        return {
          status: 'error',
          errors: [
            {
              field: '',
              message: `GitHub error: ${result.error} — ${result.error_description ?? ''}`,
            },
          ],
        };
      }

      // Success — we have the token
      if ('access_token' in result && result.access_token) {
        // Verify the token works
        s.config.token = result.access_token;
        const auth = await checkAuth();
        if (!auth.authenticated) {
          return {
            status: 'error',
            errors: [{ field: '', message: 'Token received but authentication check failed.' }],
          };
        }

        // Store tokens
        globalThis.githubOAuth.storeTokens(clientId, result, auth.username);

        // Clean up transient state
        delete (s as unknown as Record<string, unknown>).__deviceCode;
        delete (s as unknown as Record<string, unknown>).__deviceInterval;
        delete (s as unknown as Record<string, unknown>).__deviceClientId;
        delete (s as unknown as Record<string, unknown>).__deviceExpiresAt;

        // Persist non-sensitive info to config file
        data.write('config.json', JSON.stringify({ username: auth.username }, null, 2));
        publishState();

        console.log(`[github] Setup complete — connected as @${auth.username}`);
        return { status: 'complete' };
      }
    } catch (e) {
      console.warn(`[github] Poll attempt ${i + 1} failed: ${e}`);
    }
  }

  // If we get here, user hasn't authorized yet after all attempts
  return {
    status: 'error',
    errors: [
      {
        field: '',
        message:
          'Authorization not yet completed. Please make sure you entered the code at github.com/login/device and approved the app, then try setup again.',
      },
    ],
  };
}

async function onSetupCancel(): Promise<void> {
  console.log('[github] Setup cancelled');
}

// ---------------------------------------------------------------------------
// Disconnect
// ---------------------------------------------------------------------------

async function onDisconnect(): Promise<void> {
  console.log('[github] Disconnecting');
  const s = getSkillState();
  s.config.token = '';
  s.config.username = '';
  s.config.refreshToken = '';
  s.config.tokenExpiresAt = 0;
  s.config.refreshTokenExpiresAt = 0;
  s.config.clientId = '';
  s.authenticated = false;
  state.set('config', s.config);
  data.write('config.json', '{}');
  publishState();
}

// ---------------------------------------------------------------------------
// Options (runtime-configurable tool category toggles)
// ---------------------------------------------------------------------------

async function onListOptions(): Promise<{ options: SkillOption[] }> {
  const s = getSkillState();
  return {
    options: [
      {
        name: 'enableRepoTools',
        type: 'boolean',
        label: 'Repository Management',
        description:
          '12 tools — create, delete, fork, clone repos, manage collaborators and topics',
        value: s.config.enableRepoTools,
      },
      {
        name: 'enableIssueTools',
        type: 'boolean',
        label: 'Issues',
        description: '12 tools — create, edit, close, reopen issues, manage labels and assignees',
        value: s.config.enableIssueTools,
      },
      {
        name: 'enablePrTools',
        type: 'boolean',
        label: 'Pull Requests',
        description: '16 tools — create, edit, merge, review PRs, view diffs and checks',
        value: s.config.enablePrTools,
      },
      {
        name: 'enableSearchTools',
        type: 'boolean',
        label: 'Search',
        description: '4 tools — search repos, issues, code, and commits',
        value: s.config.enableSearchTools,
      },
      {
        name: 'enableCodeTools',
        type: 'boolean',
        label: 'Code & Files',
        description: '3 tools — view files, list directories, get README',
        value: s.config.enableCodeTools,
      },
      {
        name: 'enableReleaseTools',
        type: 'boolean',
        label: 'Releases',
        description: '6 tools — create, delete, get, list releases and assets',
        value: s.config.enableReleaseTools,
      },
      {
        name: 'enableGistTools',
        type: 'boolean',
        label: 'Gists',
        description: '6 tools — create, edit, delete, clone, get, and list gists',
        value: s.config.enableGistTools,
      },
      {
        name: 'enableWorkflowTools',
        type: 'boolean',
        label: 'Actions & Workflows',
        description: '9 tools — list, trigger, rerun, cancel workflows and view run logs',
        value: s.config.enableWorkflowTools,
      },
      {
        name: 'enableNotificationTools',
        type: 'boolean',
        label: 'Notifications & Raw API',
        description: '4 tools — list notifications, mark read, and raw API access',
        value: s.config.enableNotificationTools,
      },
    ],
  };
}

async function onSetOption(args: { name: string; value: unknown }): Promise<void> {
  const { name, value } = args;
  const s = getSkillState();

  const booleanOptions = [
    'enableRepoTools',
    'enableIssueTools',
    'enablePrTools',
    'enableSearchTools',
    'enableCodeTools',
    'enableReleaseTools',
    'enableGistTools',
    'enableWorkflowTools',
    'enableNotificationTools',
  ] as const;

  for (const opt of booleanOptions) {
    if (name === opt) {
      (s.config as unknown as Record<string, unknown>)[opt] = !!value;
      break;
    }
  }

  state.set('config', s.config);
  publishState();
  console.log(`[github] Option '${name}' set to ${value}`);
}

// ---------------------------------------------------------------------------
// Session lifecycle
// ---------------------------------------------------------------------------

async function onSessionStart(args: { sessionId: string }): Promise<void> {
  const s = getSkillState();
  s.activeSessions.push(args.sessionId);
  console.log(`[github] Session started: ${args.sessionId}`);
}

async function onSessionEnd(args: { sessionId: string }): Promise<void> {
  const s = getSkillState();
  s.activeSessions = s.activeSessions.filter(sid => sid !== args.sessionId);
  console.log(`[github] Session ended: ${args.sessionId}`);
}

// ---------------------------------------------------------------------------
// State publishing
// ---------------------------------------------------------------------------

function publishState(): void {
  const s = getSkillState();
  state.setPartial({
    connection_status: s.authenticated ? 'connected' : 'disconnected',
    auth_status: s.authenticated ? 'authenticated' : 'not_authenticated',
    username: s.config.username || null,
    is_initialized: true,
  });
}

// ---------------------------------------------------------------------------
// Expose functions on globalThis
// ---------------------------------------------------------------------------

const _g = globalThis as Record<string, unknown>;
_g.publishState = publishState;
_g.checkNotifications = checkNotifications;

// Lifecycle hooks
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

// ---------------------------------------------------------------------------
// Build active tool list based on enabled categories
// ---------------------------------------------------------------------------

// Register all tools (enabled categories). Categories disabled at runtime will
// still be registered but the tool execute will check state.
// For simplicity, we register all possible tools and let each execute handle auth.
// Be defensive in case any imported tool collection is undefined or not an array.
function asToolArray<T>(maybeTools: T[] | T | null | undefined): T[] {
  if (!maybeTools) return [];
  return Array.isArray(maybeTools) ? maybeTools : [maybeTools];
}

const tools: ToolDefinition[] = [
  ...asToolArray(repoTools),
  ...asToolArray(issueTools),
  ...asToolArray(prTools),
  ...asToolArray(searchTools),
  ...asToolArray(codeTools),
  ...asToolArray(releaseTools),
  ...asToolArray(gistTools),
  ...asToolArray(actionsTools),
  ...asToolArray(notificationTools),
  ...asToolArray(apiTools),
];

_g.tools = tools;

const skill: Skill = {
  info: {
    id: 'github',
    name: 'GitHub',
    version: '1.0.0',
    description:
      'GitHub integration via REST API — 72 tools for repos, issues, PRs, releases, gists, actions, search, notifications, and raw API access.',
    auto_start: true,
    setup: { required: true, label: 'Connect GitHub' },
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
  onDisconnect,
};

export default skill;
