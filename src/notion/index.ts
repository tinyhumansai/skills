/* eslint-disable no-undef */
// notion/index.ts
// Notion integration skill exposing 22 tools for the Notion API.
// Supports pages, databases, blocks, users, and comments.
// Supports both OAuth (preferred) and manual token authentication.

// ---------------------------------------------------------------------------
// OAuth Configuration (Public Integration)
// ---------------------------------------------------------------------------

const OAUTH_CONFIG = {
  provider: 'notion',
  clientId: '2fed872b-594c-8064-b8b2-0037ae321507',
  // Note: clientSecret is stored securely in the Rust backend, not here
  authorizeUrl: 'https://api.notion.com/v1/oauth/authorize',
  tokenUrl: 'https://api.notion.com/v1/oauth/token',
  redirectUri: 'alphahuman://oauth/notion/callback',
};

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

interface NotionConfig {
  token: string; // Legacy manual token (fallback)
  workspaceName: string;
  workspaceId: string;
  authMethod: 'oauth' | 'token' | '';
}

const CONFIG: NotionConfig = {
  token: '',
  workspaceName: '',
  workspaceId: '',
  authMethod: '',
};

const NOTION_VERSION = '2022-06-28';
const NOTION_BASE_URL = 'https://api.notion.com/v1';

// ---------------------------------------------------------------------------
// OAuth Helpers
// ---------------------------------------------------------------------------

/**
 * Check if OAuth bridge is available in the runtime.
 */
function isOAuthAvailable(): boolean {
  return typeof oauth !== 'undefined' && typeof oauth.isAvailable === 'function' && oauth.isAvailable();
}

/**
 * Check if we have valid OAuth credentials.
 */
function hasOAuthCredentials(): boolean {
  if (!isOAuthAvailable()) return false;
  return oauth.hasCredentials(OAUTH_CONFIG.provider);
}

/**
 * Get the current access token (from OAuth or legacy config).
 */
function getAccessToken(): string | null {
  // Prefer OAuth credentials
  if (hasOAuthCredentials()) {
    const creds = oauth.getCredentials(OAUTH_CONFIG.provider);
    return creds?.accessToken || null;
  }
  // Fall back to legacy manual token
  return CONFIG.token || null;
}

/**
 * Check if we're connected (have valid credentials).
 */
function isConnected(): boolean {
  return !!getAccessToken();
}

// ---------------------------------------------------------------------------
// Lifecycle hooks
// ---------------------------------------------------------------------------

function init(): void {
  console.log('[notion] Initializing');

  // Load persisted config from store
  const saved = store.get('config') as Partial<NotionConfig> | null;
  if (saved) {
    CONFIG.token = saved.token ?? '';
    CONFIG.workspaceName = saved.workspaceName ?? '';
    CONFIG.workspaceId = saved.workspaceId ?? '';
    CONFIG.authMethod = saved.authMethod ?? '';
  }

  // Determine connection status
  if (hasOAuthCredentials()) {
    const creds = oauth.getCredentials(OAUTH_CONFIG.provider);
    const wsName = creds?.workspaceName || CONFIG.workspaceName || '(unnamed)';
    console.log(`[notion] Connected via OAuth to workspace: ${wsName}`);
    CONFIG.authMethod = 'oauth';
  } else if (CONFIG.token) {
    console.log(`[notion] Connected via token to workspace: ${CONFIG.workspaceName || '(unnamed)'}`);
    CONFIG.authMethod = 'token';
  } else {
    console.log('[notion] No credentials configured — waiting for setup');
    CONFIG.authMethod = '';
  }

  // Publish initial state
  publishState();
}

function start(): void {
  if (!isConnected()) {
    console.log('[notion] No credentials — skill inactive until setup completes');
    return;
  }

  console.log('[notion] Started');
  publishState();
}

function stop(): void {
  console.log('[notion] Stopped');
  state.set('status', 'stopped');
}

// ---------------------------------------------------------------------------
// Setup flow (OAuth preferred, manual token fallback)
// ---------------------------------------------------------------------------

function onSetupStart(): SetupStartResult {
  // Check if already connected via OAuth
  if (hasOAuthCredentials()) {
    const creds = oauth.getCredentials(OAUTH_CONFIG.provider);
    return {
      step: {
        id: 'already-connected',
        title: 'Already Connected',
        description: `Connected to Notion workspace: ${creds?.workspaceName || CONFIG.workspaceName || 'Unknown'}`,
        fields: [
          {
            name: 'action',
            type: 'select',
            label: 'What would you like to do?',
            options: [
              { label: 'Keep current connection', value: 'keep' },
              { label: 'Connect different workspace', value: 'reconnect' },
            ],
          },
        ],
      },
    };
  }

  // Check if already connected via legacy token
  if (CONFIG.token) {
    return {
      step: {
        id: 'migrate',
        title: 'Upgrade to OAuth',
        description:
          'Your Notion is connected using a manual token. ' +
          'We recommend upgrading to OAuth for better security and easier management.',
        fields: [
          {
            name: 'action',
            type: 'select',
            label: 'What would you like to do?',
            options: [
              { label: 'Upgrade to OAuth (recommended)', value: 'oauth' },
              { label: 'Keep using manual token', value: 'keep' },
            ],
          },
        ],
      },
    };
  }

  // Fresh setup - prefer OAuth if available
  if (isOAuthAvailable()) {
    return {
      step: {
        id: 'oauth',
        title: 'Connect to Notion',
        description:
          'Click the button below to connect your Notion workspace. ' +
          "You'll be redirected to Notion to grant access.",
        fields: [
          {
            name: 'startOAuth',
            type: 'boolean',
            label: 'Connect with Notion',
            description: 'Opens Notion in your browser to authorize access',
            default: false,
          },
          {
            name: 'workspaceLabel',
            type: 'text',
            label: 'Workspace Label (optional)',
            description: 'A friendly name to identify this connection',
            required: false,
            placeholder: 'My Workspace',
          },
        ],
      },
    };
  }

  // OAuth not available - use manual token entry
  return {
    step: {
      id: 'token',
      title: 'Connect Notion Workspace',
      description:
        'Enter your Notion Integration Token from notion.so/my-integrations. ' +
        'Make sure the integration has access to the pages and databases you want to use.',
      fields: [
        {
          name: 'token',
          type: 'password',
          label: 'Integration Token',
          description: 'Starts with ntn_ or secret_',
          required: true,
          placeholder: 'ntn_...',
        },
        {
          name: 'workspaceName',
          type: 'text',
          label: 'Workspace Label (optional)',
          description: 'A friendly name to identify this workspace',
          required: false,
          placeholder: 'My Workspace',
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

  // Handle "already connected" step
  if (stepId === 'already-connected') {
    if (values.action === 'keep') {
      return { status: 'complete' };
    }
    // Reconnect - revoke current credentials and restart
    if (hasOAuthCredentials()) {
      oauth.revokeCredentials(OAUTH_CONFIG.provider);
    }
    CONFIG.token = '';
    CONFIG.authMethod = '';
    store.delete('config');
    return {
      status: 'next',
      nextStep: onSetupStart().step,
    };
  }

  // Handle migration step
  if (stepId === 'migrate') {
    if (values.action === 'keep') {
      return { status: 'complete' };
    }
    // Clear legacy token and proceed to OAuth
    CONFIG.token = '';
    store.set('config', CONFIG);
    return {
      status: 'next',
      nextStep: {
        id: 'oauth',
        title: 'Connect to Notion',
        description:
          'Click the button below to connect your Notion workspace. ' +
          "You'll be redirected to Notion to grant access.",
        fields: [
          {
            name: 'startOAuth',
            type: 'boolean',
            label: 'Connect with Notion',
            description: 'Opens Notion in your browser to authorize access',
            default: false,
          },
          {
            name: 'workspaceLabel',
            type: 'text',
            label: 'Workspace Label (optional)',
            description: 'A friendly name to identify this connection',
            required: false,
            placeholder: 'My Workspace',
          },
        ],
      },
    };
  }

  // Handle OAuth step
  if (stepId === 'oauth') {
    const startOAuth = values.startOAuth as boolean;
    const workspaceLabel = ((values.workspaceLabel as string) ?? '').trim();

    // Check if OAuth was triggered
    if (startOAuth && isOAuthAvailable()) {
      // Start OAuth flow
      try {
        const flowHandle = oauth.startFlow(OAUTH_CONFIG.provider, {
          redirectUri: OAUTH_CONFIG.redirectUri,
        });

        // Return a "waiting" step that polls for completion
        return {
          status: 'next',
          nextStep: {
            id: 'oauth-pending',
            title: 'Waiting for Authorization',
            description:
              'Please complete the authorization in your browser. ' +
              'This page will update automatically when complete.',
            fields: [
              {
                name: 'flowId',
                type: 'text',
                label: 'Flow ID',
                default: flowHandle.flowId,
              },
              {
                name: 'workspaceLabel',
                type: 'text',
                label: 'Workspace Label',
                default: workspaceLabel,
              },
            ],
          },
        };
      } catch (e) {
        return {
          status: 'error',
          errors: [{ field: 'startOAuth', message: `Failed to start OAuth: ${e}` }],
        };
      }
    }

    // Check if OAuth is already complete (user returned from browser)
    if (hasOAuthCredentials()) {
      const creds = oauth.getCredentials(OAUTH_CONFIG.provider);
      CONFIG.workspaceName = workspaceLabel || creds?.workspaceName || '';
      CONFIG.workspaceId = creds?.workspaceId || '';
      CONFIG.authMethod = 'oauth';
      CONFIG.token = ''; // Clear any legacy token
      store.set('config', CONFIG);

      console.log(`[notion] OAuth complete — connected to ${CONFIG.workspaceName || 'workspace'}`);
      publishState();
      return { status: 'complete' };
    }

    return {
      status: 'error',
      errors: [{ field: 'startOAuth', message: 'Please click to connect your Notion account' }],
    };
  }

  // Handle OAuth pending step (polling for completion)
  if (stepId === 'oauth-pending') {
    const flowId = values.flowId as string;
    const workspaceLabel = ((values.workspaceLabel as string) ?? '').trim();

    if (isOAuthAvailable() && flowId) {
      const flowStatus = oauth.checkFlow(flowId);

      if (flowStatus.status === 'complete') {
        const creds = oauth.getCredentials(OAUTH_CONFIG.provider);
        CONFIG.workspaceName = workspaceLabel || creds?.workspaceName || '';
        CONFIG.workspaceId = creds?.workspaceId || '';
        CONFIG.authMethod = 'oauth';
        CONFIG.token = '';
        store.set('config', CONFIG);

        console.log(`[notion] OAuth complete — connected to ${CONFIG.workspaceName || 'workspace'}`);
        publishState();
        return { status: 'complete' };
      }

      if (flowStatus.status === 'failed') {
        return {
          status: 'error',
          errors: [{ field: '', message: flowStatus.error || 'OAuth authorization failed' }],
        };
      }

      if (flowStatus.status === 'expired') {
        return {
          status: 'error',
          errors: [{ field: '', message: 'Authorization timed out. Please try again.' }],
        };
      }

      // Still pending - this shouldn't normally happen in submit, but handle it
      return {
        status: 'error',
        errors: [{ field: '', message: 'Authorization still pending. Please complete it in your browser.' }],
      };
    }

    return {
      status: 'error',
      errors: [{ field: '', message: 'OAuth flow not found' }],
    };
  }

  // Handle manual token step (legacy fallback)
  if (stepId === 'token') {
    const token = ((values.token as string) ?? '').trim();
    const workspaceName = ((values.workspaceName as string) ?? '').trim();

    // Validate token format
    if (!token) {
      return {
        status: 'error',
        errors: [{ field: 'token', message: 'Integration token is required' }],
      };
    }

    if (!token.startsWith('ntn_') && !token.startsWith('secret_')) {
      return {
        status: 'error',
        errors: [{ field: 'token', message: 'Token should start with ntn_ or secret_' }],
      };
    }

    // Validate token by calling users/me
    try {
      const response = net.fetch(`${NOTION_BASE_URL}/users/me`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Notion-Version': NOTION_VERSION,
          'Content-Type': 'application/json',
        },
        timeout: 15,
      });

      if (response.status === 401) {
        return {
          status: 'error',
          errors: [{ field: 'token', message: 'Invalid token — unauthorized' }],
        };
      }

      if (response.status >= 400) {
        return {
          status: 'error',
          errors: [{ field: 'token', message: `Notion API error: ${response.status}` }],
        };
      }

      const user = JSON.parse(response.body);
      console.log(`[notion] Authenticated as: ${user.name || user.id}`);
    } catch (e) {
      return {
        status: 'error',
        errors: [{ field: 'token', message: `Failed to connect: ${formatApiError(e)}` }],
      };
    }

    // Store config
    CONFIG.token = token;
    CONFIG.workspaceName = workspaceName;
    CONFIG.authMethod = 'token';
    store.set('config', CONFIG);
    data.write('config.json', JSON.stringify({ workspaceName }, null, 2));

    console.log(`[notion] Setup complete — connected to ${workspaceName || 'workspace'}`);
    publishState();

    return { status: 'complete' };
  }

  return { status: 'error', errors: [{ field: '', message: `Unknown setup step: ${stepId}` }] };
}

function onSetupCancel(): void {
  console.log('[notion] Setup cancelled');
}

// ---------------------------------------------------------------------------
// Disconnect
// ---------------------------------------------------------------------------

function onDisconnect(): void {
  console.log('[notion] Disconnecting');

  // Revoke OAuth credentials if present
  if (hasOAuthCredentials()) {
    oauth.revokeCredentials(OAUTH_CONFIG.provider);
  }

  // Clear config
  CONFIG.token = '';
  CONFIG.workspaceName = '';
  CONFIG.workspaceId = '';
  CONFIG.authMethod = '';

  store.delete('config');

  publishState();
  console.log('[notion] Disconnected');
}

// ---------------------------------------------------------------------------
// State publishing
// ---------------------------------------------------------------------------

function publishState(): void {
  const connected = isConnected();
  let workspaceName: string | null = CONFIG.workspaceName || null;
  let workspaceId: string | null = CONFIG.workspaceId || null;

  // Get workspace info from OAuth credentials if available
  if (hasOAuthCredentials()) {
    const creds = oauth.getCredentials(OAUTH_CONFIG.provider);
    workspaceName = workspaceName || creds?.workspaceName || null;
    workspaceId = workspaceId || creds?.workspaceId || null;
  }

  state.setPartial({
    connected,
    workspaceName,
    workspaceId,
    authMethod: CONFIG.authMethod || null,
  });
}

// ---------------------------------------------------------------------------
// Notion API helpers
// ---------------------------------------------------------------------------

function notionFetch(endpoint: string, options: { method?: string; body?: unknown } = {}): unknown {
  const token = getAccessToken();

  if (!token) {
    throw new Error('Notion not connected. Please complete setup first.');
  }

  const response = net.fetch(`${NOTION_BASE_URL}${endpoint}`, {
    method: options.method || 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
      'Notion-Version': NOTION_VERSION,
      'Content-Type': 'application/json',
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    timeout: 30,
  });

  // Handle token revocation
  if (response.status === 401) {
    // Token may have been revoked by user in Notion
    if (hasOAuthCredentials()) {
      console.log('[notion] Access token rejected — revoking credentials');
      oauth.revokeCredentials(OAUTH_CONFIG.provider);
    }
    CONFIG.token = '';
    CONFIG.authMethod = '';
    publishState();
    throw new Error('Notion access revoked. Please reconnect in settings.');
  }

  if (response.status >= 400) {
    const errorBody = response.body;
    let message = `Notion API error: ${response.status}`;
    try {
      const parsed = JSON.parse(errorBody);
      if (parsed.message) {
        message = parsed.message;
      }
    } catch {
      // Use default message
    }
    throw new Error(message);
  }

  return JSON.parse(response.body);
}

function formatApiError(error: unknown): string {
  const message = String(error);

  if (message.includes('401')) {
    return 'Unauthorized. Check that your integration token is valid.';
  }
  if (message.includes('404')) {
    return 'Not found. Make sure the page/database is shared with your integration.';
  }
  if (message.includes('429')) {
    return 'Rate limited. Please try again in a moment.';
  }
  if (message.includes('403')) {
    return 'Forbidden. The integration may not have access to this resource.';
  }

  return message;
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function formatRichText(richText: unknown[]): string {
  if (!Array.isArray(richText)) return '';
  return richText
    .map(rt => {
      const item = rt as Record<string, unknown>;
      return (item.plain_text as string) || '';
    })
    .join('');
}

function formatPageTitle(page: Record<string, unknown>): string {
  const props = page.properties as Record<string, unknown>;
  if (!props) return page.id as string;

  // Find title property
  for (const key of Object.keys(props)) {
    const prop = props[key] as Record<string, unknown>;
    if (prop.type === 'title' && Array.isArray(prop.title)) {
      const title = formatRichText(prop.title);
      if (title) return title;
    }
  }

  return page.id as string;
}

function formatPageSummary(page: Record<string, unknown>): Record<string, unknown> {
  return {
    id: page.id,
    title: formatPageTitle(page),
    url: page.url,
    created_time: page.created_time,
    last_edited_time: page.last_edited_time,
    archived: page.archived,
    parent_type: (page.parent as Record<string, unknown>)?.type,
  };
}

function formatDatabaseSummary(db: Record<string, unknown>): Record<string, unknown> {
  const title = Array.isArray(db.title) ? formatRichText(db.title) : '';
  return {
    id: db.id,
    title: title || '(Untitled)',
    url: db.url,
    created_time: db.created_time,
    last_edited_time: db.last_edited_time,
    property_count: Object.keys(db.properties || {}).length,
  };
}

function formatBlockContent(block: Record<string, unknown>): string {
  const type = block.type as string;
  const content = block[type] as Record<string, unknown> | undefined;

  if (!content) return `[${type}]`;

  // Handle rich text blocks
  if (content.rich_text && Array.isArray(content.rich_text)) {
    const text = formatRichText(content.rich_text);
    return text || `[empty ${type}]`;
  }

  // Handle child blocks reference
  if (content.children) {
    return `[${type} with children]`;
  }

  return `[${type}]`;
}

function formatBlockSummary(block: Record<string, unknown>): Record<string, unknown> {
  return {
    id: block.id,
    type: block.type,
    has_children: block.has_children,
    content: formatBlockContent(block),
  };
}

function formatUserSummary(user: Record<string, unknown>): Record<string, unknown> {
  return { id: user.id, name: user.name, type: user.type, avatar_url: user.avatar_url };
}

// ---------------------------------------------------------------------------
// Rich text builders for creating content
// ---------------------------------------------------------------------------

function buildRichText(text: string): unknown[] {
  return [{ type: 'text', text: { content: text } }];
}

function buildParagraphBlock(text: string): Record<string, unknown> {
  return { object: 'block', type: 'paragraph', paragraph: { rich_text: buildRichText(text) } };
}

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

const notionTools: ToolDefinition[] = [
  // =========================================================================
  // PAGES (8 tools)
  // =========================================================================

  {
    name: 'notion-search',
    description:
      'Search for pages and databases in your Notion workspace. ' +
      'Can filter by type (page or database) and returns matching results.',
    input_schema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query (optional, returns recent if empty)' },
        filter: {
          type: 'string',
          enum: ['page', 'database'],
          description: 'Filter results by type',
        },
        page_size: {
          type: 'number',
          description: 'Number of results to return (default 20, max 100)',
        },
      },
    },
    execute(args: Record<string, unknown>): string {
      try {
        const query = ((args.query as string) || '').trim();
        const filter = args.filter as string | undefined;
        const pageSize = Math.min((args.page_size as number) || 20, 100);

        const body: Record<string, unknown> = { page_size: pageSize };
        if (query) body.query = query;
        if (filter) body.filter = { property: 'object', value: filter };

        const result = notionFetch('/search', { method: 'POST', body }) as {
          results: Record<string, unknown>[];
          has_more: boolean;
        };

        const formatted = result.results.map(item => {
          if (item.object === 'page') {
            return { object: 'page', ...formatPageSummary(item) };
          } else if (item.object === 'database') {
            return { object: 'database', ...formatDatabaseSummary(item) };
          }
          return { object: item.object, id: item.id };
        });

        return JSON.stringify({
          count: formatted.length,
          has_more: result.has_more,
          results: formatted,
        });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-get-page',
    description:
      "Get a page's metadata and properties by its ID. " +
      'Use notion-get-page-content to get the actual content/blocks.',
    input_schema: {
      type: 'object',
      properties: {
        page_id: {
          type: 'string',
          description: 'The page ID (UUID format, with or without dashes)',
        },
      },
      required: ['page_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const pageId = (args.page_id as string) || '';
        if (!pageId) {
          return JSON.stringify({ error: 'page_id is required' });
        }

        const page = notionFetch(`/pages/${pageId}`) as Record<string, unknown>;

        return JSON.stringify({ ...formatPageSummary(page), properties: page.properties });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-create-page',
    description:
      'Create a new page in Notion. Parent can be another page or a database. ' +
      'For database parents, properties must match the database schema.',
    input_schema: {
      type: 'object',
      properties: {
        parent_id: { type: 'string', description: 'Parent page ID or database ID' },
        parent_type: {
          type: 'string',
          enum: ['page_id', 'database_id'],
          description: 'Type of parent (default: page_id)',
        },
        title: { type: 'string', description: 'Page title' },
        content: {
          type: 'string',
          description: 'Initial text content (creates a paragraph block)',
        },
        properties: {
          type: 'string',
          description: 'JSON string of additional properties (for database pages)',
        },
      },
      required: ['parent_id', 'title'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const parentId = (args.parent_id as string) || '';
        const parentType = (args.parent_type as string) || 'page_id';
        const title = (args.title as string) || '';
        const content = args.content as string | undefined;
        const propsJson = args.properties as string | undefined;

        if (!parentId) {
          return JSON.stringify({ error: 'parent_id is required' });
        }
        if (!title) {
          return JSON.stringify({ error: 'title is required' });
        }

        const body: Record<string, unknown> = { parent: { [parentType]: parentId } };

        // Set properties based on parent type
        if (parentType === 'database_id') {
          // For database pages, title goes in a title property
          let props: Record<string, unknown> = { Name: { title: buildRichText(title) } };
          if (propsJson) {
            try {
              const additional = JSON.parse(propsJson);
              props = { ...props, ...additional };
            } catch {
              return JSON.stringify({ error: 'Invalid properties JSON' });
            }
          }
          body.properties = props;
        } else {
          // For regular pages
          body.properties = { title: { title: buildRichText(title) } };
        }

        // Add initial content if provided
        if (content) {
          body.children = [buildParagraphBlock(content)];
        }

        const page = notionFetch('/pages', { method: 'POST', body }) as Record<string, unknown>;

        return JSON.stringify({ success: true, page: formatPageSummary(page) });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-update-page',
    description:
      "Update a page's properties. Can update title and other properties. " +
      'Use notion-append-text to add content blocks.',
    input_schema: {
      type: 'object',
      properties: {
        page_id: { type: 'string', description: 'The page ID to update' },
        title: { type: 'string', description: 'New title (optional)' },
        properties: { type: 'string', description: 'JSON string of properties to update' },
        archived: {
          type: 'string',
          enum: ['true', 'false'],
          description: 'Set to true to archive the page',
        },
      },
      required: ['page_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const pageId = (args.page_id as string) || '';
        const title = args.title as string | undefined;
        const propsJson = args.properties as string | undefined;
        const archived = args.archived as string | undefined;

        if (!pageId) {
          return JSON.stringify({ error: 'page_id is required' });
        }

        const body: Record<string, unknown> = {};

        if (title) {
          body.properties = { title: { title: buildRichText(title) } };
        }

        if (propsJson) {
          try {
            const props = JSON.parse(propsJson) as Record<string, unknown>;
            const existingProps = (body.properties || {}) as Record<string, unknown>;
            body.properties = { ...existingProps, ...props };
          } catch {
            return JSON.stringify({ error: 'Invalid properties JSON' });
          }
        }

        if (archived !== undefined) {
          body.archived = archived === 'true';
        }

        if (Object.keys(body).length === 0) {
          return JSON.stringify({ error: 'No updates specified' });
        }

        const page = notionFetch(`/pages/${pageId}`, { method: 'PATCH', body }) as Record<
          string,
          unknown
        >;

        return JSON.stringify({ success: true, page: formatPageSummary(page) });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-delete-page',
    description: "Delete (archive) a page. Archived pages can be restored from Notion's trash.",
    input_schema: {
      type: 'object',
      properties: { page_id: { type: 'string', description: 'The page ID to delete/archive' } },
      required: ['page_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const pageId = (args.page_id as string) || '';
        if (!pageId) {
          return JSON.stringify({ error: 'page_id is required' });
        }

        const page = notionFetch(`/pages/${pageId}`, {
          method: 'PATCH',
          body: { archived: true },
        }) as Record<string, unknown>;

        return JSON.stringify({
          success: true,
          message: 'Page archived',
          page: formatPageSummary(page),
        });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-get-page-content',
    description:
      'Get the content blocks of a page. Returns the text and structure of the page. ' +
      'Use recursive=true to also get nested blocks.',
    input_schema: {
      type: 'object',
      properties: {
        page_id: { type: 'string', description: 'The page ID to get content from' },
        recursive: {
          type: 'string',
          enum: ['true', 'false'],
          description: 'Whether to fetch nested blocks (default: false)',
        },
        page_size: {
          type: 'number',
          description: 'Number of blocks to return (default 50, max 100)',
        },
      },
      required: ['page_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const pageId = (args.page_id as string) || '';
        const recursive = args.recursive === 'true';
        const pageSize = Math.min((args.page_size as number) || 50, 100);

        if (!pageId) {
          return JSON.stringify({ error: 'page_id is required' });
        }

        const result = notionFetch(`/blocks/${pageId}/children?page_size=${pageSize}`) as {
          results: Record<string, unknown>[];
          has_more: boolean;
        };

        const blocks = result.results.map(block => {
          const summary = formatBlockSummary(block);

          // Recursively fetch children if requested
          if (recursive && block.has_children) {
            try {
              const children = notionFetch(`/blocks/${block.id}/children?page_size=50`) as {
                results: Record<string, unknown>[];
              };
              return { ...summary, children: children.results.map(formatBlockSummary) };
            } catch {
              return { ...summary, children: [] };
            }
          }

          return summary;
        });

        return JSON.stringify({
          page_id: pageId,
          block_count: blocks.length,
          has_more: result.has_more,
          blocks,
        });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-list-all-pages',
    description: 'List all pages in the workspace that the integration has access to.',
    input_schema: {
      type: 'object',
      properties: {
        page_size: {
          type: 'number',
          description: 'Number of results to return (default 20, max 100)',
        },
      },
    },
    execute(args: Record<string, unknown>): string {
      try {
        const pageSize = Math.min((args.page_size as number) || 20, 100);

        const result = notionFetch('/search', {
          method: 'POST',
          body: { filter: { property: 'object', value: 'page' }, page_size: pageSize },
        }) as { results: Record<string, unknown>[]; has_more: boolean };

        const pages = result.results.map(formatPageSummary);

        return JSON.stringify({ count: pages.length, has_more: result.has_more, pages });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-append-text',
    description:
      'Append text content to a page or block. Creates paragraph blocks with the given text.',
    input_schema: {
      type: 'object',
      properties: {
        block_id: { type: 'string', description: 'The page or block ID to append to' },
        text: { type: 'string', description: 'Text content to append' },
      },
      required: ['block_id', 'text'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const blockId = (args.block_id as string) || '';
        const text = (args.text as string) || '';

        if (!blockId) {
          return JSON.stringify({ error: 'block_id is required' });
        }
        if (!text) {
          return JSON.stringify({ error: 'text is required' });
        }

        // Split text by newlines to create multiple paragraphs
        const paragraphs = text.split('\n').filter(p => p.trim());
        const children = paragraphs.map(buildParagraphBlock);

        const result = notionFetch(`/blocks/${blockId}/children`, {
          method: 'PATCH',
          body: { children },
        }) as { results: Record<string, unknown>[] };

        return JSON.stringify({
          success: true,
          blocks_added: result.results.length,
          blocks: result.results.map(formatBlockSummary),
        });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  // =========================================================================
  // DATABASES (5 tools)
  // =========================================================================

  {
    name: 'notion-query-database',
    description: 'Query a database with optional filters and sorts. Returns database rows/pages.',
    input_schema: {
      type: 'object',
      properties: {
        database_id: { type: 'string', description: 'The database ID to query' },
        filter: {
          type: 'string',
          description: 'JSON string of filter object (Notion filter syntax)',
        },
        sorts: { type: 'string', description: 'JSON string of sorts array (Notion sort syntax)' },
        page_size: { type: 'number', description: 'Number of results (default 20, max 100)' },
      },
      required: ['database_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const databaseId = (args.database_id as string) || '';
        const filterJson = args.filter as string | undefined;
        const sortsJson = args.sorts as string | undefined;
        const pageSize = Math.min((args.page_size as number) || 20, 100);

        if (!databaseId) {
          return JSON.stringify({ error: 'database_id is required' });
        }

        const body: Record<string, unknown> = { page_size: pageSize };

        if (filterJson) {
          try {
            body.filter = JSON.parse(filterJson);
          } catch {
            return JSON.stringify({ error: 'Invalid filter JSON' });
          }
        }

        if (sortsJson) {
          try {
            body.sorts = JSON.parse(sortsJson);
          } catch {
            return JSON.stringify({ error: 'Invalid sorts JSON' });
          }
        }

        const result = notionFetch(`/databases/${databaseId}/query`, { method: 'POST', body }) as {
          results: Record<string, unknown>[];
          has_more: boolean;
        };

        const rows = result.results.map(page => ({
          ...formatPageSummary(page),
          properties: page.properties,
        }));

        return JSON.stringify({ count: rows.length, has_more: result.has_more, rows });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-get-database',
    description: "Get a database's schema and metadata. Shows all properties and their types.",
    input_schema: {
      type: 'object',
      properties: { database_id: { type: 'string', description: 'The database ID' } },
      required: ['database_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const databaseId = (args.database_id as string) || '';
        if (!databaseId) {
          return JSON.stringify({ error: 'database_id is required' });
        }

        const db = notionFetch(`/databases/${databaseId}`) as Record<string, unknown>;

        // Format properties schema
        const props = db.properties as Record<string, unknown>;
        const schema: Record<string, unknown> = {};
        for (const [name, prop] of Object.entries(props)) {
          const propData = prop as Record<string, unknown>;
          schema[name] = { type: propData.type, id: propData.id };
        }

        return JSON.stringify({ ...formatDatabaseSummary(db), schema });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-create-database',
    description: 'Create a new database in Notion. Must specify parent page and property schema.',
    input_schema: {
      type: 'object',
      properties: {
        parent_page_id: {
          type: 'string',
          description: 'Parent page ID where the database will be created',
        },
        title: { type: 'string', description: 'Database title' },
        properties: {
          type: 'string',
          description:
            'JSON string of properties schema. Example: {"Name":{"title":{}},"Status":{"select":{"options":[{"name":"Todo"},{"name":"Done"}]}}}',
        },
      },
      required: ['parent_page_id', 'title'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const parentId = (args.parent_page_id as string) || '';
        const title = (args.title as string) || '';
        const propsJson = args.properties as string | undefined;

        if (!parentId) {
          return JSON.stringify({ error: 'parent_page_id is required' });
        }
        if (!title) {
          return JSON.stringify({ error: 'title is required' });
        }

        // Default properties with just a title column
        let properties: Record<string, unknown> = { Name: { title: {} } };

        if (propsJson) {
          try {
            properties = JSON.parse(propsJson);
          } catch {
            return JSON.stringify({ error: 'Invalid properties JSON' });
          }
        }

        const body = { parent: { page_id: parentId }, title: buildRichText(title), properties };

        const db = notionFetch('/databases', { method: 'POST', body }) as Record<string, unknown>;

        return JSON.stringify({ success: true, database: formatDatabaseSummary(db) });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-update-database',
    description: "Update a database's title or properties schema.",
    input_schema: {
      type: 'object',
      properties: {
        database_id: { type: 'string', description: 'The database ID to update' },
        title: { type: 'string', description: 'New title (optional)' },
        properties: { type: 'string', description: 'JSON string of properties to add or update' },
      },
      required: ['database_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const databaseId = (args.database_id as string) || '';
        const title = args.title as string | undefined;
        const propsJson = args.properties as string | undefined;

        if (!databaseId) {
          return JSON.stringify({ error: 'database_id is required' });
        }

        const body: Record<string, unknown> = {};

        if (title) {
          body.title = buildRichText(title);
        }

        if (propsJson) {
          try {
            body.properties = JSON.parse(propsJson);
          } catch {
            return JSON.stringify({ error: 'Invalid properties JSON' });
          }
        }

        if (Object.keys(body).length === 0) {
          return JSON.stringify({ error: 'No updates specified' });
        }

        const db = notionFetch(`/databases/${databaseId}`, { method: 'PATCH', body }) as Record<
          string,
          unknown
        >;

        return JSON.stringify({ success: true, database: formatDatabaseSummary(db) });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-list-all-databases',
    description: 'List all databases in the workspace that the integration has access to.',
    input_schema: {
      type: 'object',
      properties: {
        page_size: { type: 'number', description: 'Number of results (default 20, max 100)' },
      },
    },
    execute(args: Record<string, unknown>): string {
      try {
        const pageSize = Math.min((args.page_size as number) || 20, 100);

        const result = notionFetch('/search', {
          method: 'POST',
          body: { filter: { property: 'object', value: 'database' }, page_size: pageSize },
        }) as { results: Record<string, unknown>[]; has_more: boolean };

        const databases = result.results.map(formatDatabaseSummary);

        return JSON.stringify({ count: databases.length, has_more: result.has_more, databases });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  // =========================================================================
  // BLOCKS (5 tools)
  // =========================================================================

  {
    name: 'notion-get-block',
    description: "Get a block by its ID. Returns the block's type and content.",
    input_schema: {
      type: 'object',
      properties: { block_id: { type: 'string', description: 'The block ID' } },
      required: ['block_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const blockId = (args.block_id as string) || '';
        if (!blockId) {
          return JSON.stringify({ error: 'block_id is required' });
        }

        const block = notionFetch(`/blocks/${blockId}`) as Record<string, unknown>;

        return JSON.stringify({ ...formatBlockSummary(block), raw: block });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-get-block-children',
    description: 'Get the children blocks of a block or page.',
    input_schema: {
      type: 'object',
      properties: {
        block_id: { type: 'string', description: 'The parent block or page ID' },
        page_size: { type: 'number', description: 'Number of blocks (default 50, max 100)' },
      },
      required: ['block_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const blockId = (args.block_id as string) || '';
        const pageSize = Math.min((args.page_size as number) || 50, 100);

        if (!blockId) {
          return JSON.stringify({ error: 'block_id is required' });
        }

        const result = notionFetch(`/blocks/${blockId}/children?page_size=${pageSize}`) as {
          results: Record<string, unknown>[];
          has_more: boolean;
        };

        return JSON.stringify({
          parent_id: blockId,
          count: result.results.length,
          has_more: result.has_more,
          children: result.results.map(formatBlockSummary),
        });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-append-blocks',
    description: 'Append child blocks to a page or block. Supports various block types.',
    input_schema: {
      type: 'object',
      properties: {
        block_id: { type: 'string', description: 'The parent page or block ID' },
        blocks: {
          type: 'string',
          description:
            'JSON string of blocks array. Example: [{"type":"paragraph","paragraph":{"rich_text":[{"text":{"content":"Hello"}}]}}]',
        },
      },
      required: ['block_id', 'blocks'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const blockId = (args.block_id as string) || '';
        const blocksJson = (args.blocks as string) || '';

        if (!blockId) {
          return JSON.stringify({ error: 'block_id is required' });
        }
        if (!blocksJson) {
          return JSON.stringify({ error: 'blocks is required' });
        }

        let children: unknown[];
        try {
          children = JSON.parse(blocksJson);
        } catch {
          return JSON.stringify({ error: 'Invalid blocks JSON' });
        }

        if (!Array.isArray(children) || children.length === 0) {
          return JSON.stringify({ error: 'blocks must be a non-empty array' });
        }

        const result = notionFetch(`/blocks/${blockId}/children`, {
          method: 'PATCH',
          body: { children },
        }) as { results: Record<string, unknown>[] };

        return JSON.stringify({
          success: true,
          blocks_added: result.results.length,
          blocks: result.results.map(formatBlockSummary),
        });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-update-block',
    description: "Update a block's content. The structure depends on the block type.",
    input_schema: {
      type: 'object',
      properties: {
        block_id: { type: 'string', description: 'The block ID to update' },
        content: {
          type: 'string',
          description:
            'JSON string of the block type content. Example for paragraph: {"paragraph":{"rich_text":[{"text":{"content":"Updated text"}}]}}',
        },
        archived: {
          type: 'string',
          enum: ['true', 'false'],
          description: 'Set to true to archive the block',
        },
      },
      required: ['block_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const blockId = (args.block_id as string) || '';
        const contentJson = args.content as string | undefined;
        const archived = args.archived as string | undefined;

        if (!blockId) {
          return JSON.stringify({ error: 'block_id is required' });
        }

        const body: Record<string, unknown> = {};

        if (contentJson) {
          try {
            const content = JSON.parse(contentJson);
            Object.assign(body, content);
          } catch {
            return JSON.stringify({ error: 'Invalid content JSON' });
          }
        }

        if (archived !== undefined) {
          body.archived = archived === 'true';
        }

        if (Object.keys(body).length === 0) {
          return JSON.stringify({ error: 'No updates specified' });
        }

        const block = notionFetch(`/blocks/${blockId}`, { method: 'PATCH', body }) as Record<
          string,
          unknown
        >;

        return JSON.stringify({ success: true, block: formatBlockSummary(block) });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-delete-block',
    description: 'Delete a block. This permanently removes the block from Notion.',
    input_schema: {
      type: 'object',
      properties: { block_id: { type: 'string', description: 'The block ID to delete' } },
      required: ['block_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const blockId = (args.block_id as string) || '';
        if (!blockId) {
          return JSON.stringify({ error: 'block_id is required' });
        }

        notionFetch(`/blocks/${blockId}`, { method: 'DELETE' });

        return JSON.stringify({ success: true, message: 'Block deleted', block_id: blockId });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  // =========================================================================
  // USERS (2 tools)
  // =========================================================================

  {
    name: 'notion-list-users',
    description: 'List all users in the workspace that the integration can see.',
    input_schema: {
      type: 'object',
      properties: {
        page_size: { type: 'number', description: 'Number of results (default 20, max 100)' },
      },
    },
    execute(args: Record<string, unknown>): string {
      try {
        const pageSize = Math.min((args.page_size as number) || 20, 100);

        const result = notionFetch(`/users?page_size=${pageSize}`) as {
          results: Record<string, unknown>[];
          has_more: boolean;
        };

        const users = result.results.map(formatUserSummary);

        return JSON.stringify({ count: users.length, has_more: result.has_more, users });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-get-user',
    description: 'Get a user by their ID.',
    input_schema: {
      type: 'object',
      properties: { user_id: { type: 'string', description: 'The user ID' } },
      required: ['user_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const userId = (args.user_id as string) || '';
        if (!userId) {
          return JSON.stringify({ error: 'user_id is required' });
        }

        const user = notionFetch(`/users/${userId}`) as Record<string, unknown>;

        return JSON.stringify(formatUserSummary(user));
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  // =========================================================================
  // COMMENTS (2 tools)
  // =========================================================================

  {
    name: 'notion-create-comment',
    description:
      'Create a comment on a page or in a discussion thread. ' +
      'Must specify either page_id (for new discussion) or discussion_id (to reply).',
    input_schema: {
      type: 'object',
      properties: {
        page_id: { type: 'string', description: 'Page ID to start a new discussion on' },
        discussion_id: {
          type: 'string',
          description: 'Discussion ID to reply to an existing thread',
        },
        text: { type: 'string', description: 'Comment text content' },
      },
      required: ['text'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const pageId = args.page_id as string | undefined;
        const discussionId = args.discussion_id as string | undefined;
        const text = (args.text as string) || '';

        if (!pageId && !discussionId) {
          return JSON.stringify({ error: 'Either page_id or discussion_id is required' });
        }
        if (!text) {
          return JSON.stringify({ error: 'text is required' });
        }

        const body: Record<string, unknown> = { rich_text: buildRichText(text) };

        if (discussionId) {
          body.discussion_id = discussionId;
        } else if (pageId) {
          body.parent = { page_id: pageId };
        }

        const comment = notionFetch('/comments', { method: 'POST', body }) as Record<
          string,
          unknown
        >;

        return JSON.stringify({
          success: true,
          comment: {
            id: comment.id,
            discussion_id: comment.discussion_id,
            created_time: comment.created_time,
            text: formatRichText(comment.rich_text as unknown[]),
          },
        });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },

  {
    name: 'notion-list-comments',
    description: 'List comments on a block or page.',
    input_schema: {
      type: 'object',
      properties: {
        block_id: { type: 'string', description: 'Block or page ID to get comments for' },
        page_size: { type: 'number', description: 'Number of results (default 20, max 100)' },
      },
      required: ['block_id'],
    },
    execute(args: Record<string, unknown>): string {
      try {
        const blockId = (args.block_id as string) || '';
        const pageSize = Math.min((args.page_size as number) || 20, 100);

        if (!blockId) {
          return JSON.stringify({ error: 'block_id is required' });
        }

        const result = notionFetch(`/comments?block_id=${blockId}&page_size=${pageSize}`) as {
          results: Record<string, unknown>[];
          has_more: boolean;
        };

        const comments = result.results.map(comment => ({
          id: comment.id,
          discussion_id: comment.discussion_id,
          created_time: comment.created_time,
          created_by: comment.created_by,
          text: formatRichText(comment.rich_text as unknown[]),
        }));

        return JSON.stringify({ count: comments.length, has_more: result.has_more, comments });
      } catch (e) {
        return JSON.stringify({ error: formatApiError(e) });
      }
    },
  },
];

const skill: Skill = {
  info: {
    id: 'notion',
    name: 'Notion',
    description: 'Notion workspace integration',
    version: '1.0.0',
    runtime: 'v8',
    entry: 'index.js',
    auto_start: false,
    setup: { required: true, label: 'Notion' },
  },
  tools: notionTools,
  init,
  start,
  stop,
  onSetupStart,
  onSetupSubmit,
  onSetupCancel,
  onDisconnect,
};

export default skill;
