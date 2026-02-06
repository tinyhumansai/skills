// Notion API helpers and formatting functions

// ---------------------------------------------------------------------------
// Notion API helpers
// ---------------------------------------------------------------------------

export function notionFetch(
  endpoint: string,
  options: { method?: string; body?: unknown } = {}
): unknown {
  if (!oauth.getCredential()) {
    throw new Error('Notion not connected. Please complete setup first.');
  }

  const response = oauth.fetch(`/v1${endpoint}`, {
    method: options.method || 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: options.body ? JSON.stringify(options.body) : undefined,
    timeout: 30,
  });

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

export function formatApiError(error: unknown): string {
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

export function formatRichText(richText: unknown[]): string {
  if (!Array.isArray(richText)) return '';
  return richText
    .map(rt => {
      const item = rt as Record<string, unknown>;
      return (item.plain_text as string) || '';
    })
    .join('');
}

export function formatPageTitle(page: Record<string, unknown>): string {
  const props = page.properties as Record<string, unknown>;
  if (!props) return page.id as string;

  for (const key of Object.keys(props)) {
    const prop = props[key] as Record<string, unknown>;
    if (prop.type === 'title' && Array.isArray(prop.title)) {
      const title = formatRichText(prop.title);
      if (title) return title;
    }
  }

  return page.id as string;
}

export function formatPageSummary(page: Record<string, unknown>): Record<string, unknown> {
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

export function formatDatabaseSummary(db: Record<string, unknown>): Record<string, unknown> {
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

export function formatBlockContent(block: Record<string, unknown>): string {
  const type = block.type as string;
  const content = block[type] as Record<string, unknown> | undefined;

  if (!content) return `[${type}]`;

  if (content.rich_text && Array.isArray(content.rich_text)) {
    const text = formatRichText(content.rich_text);
    return text || `[empty ${type}]`;
  }

  if (content.children) {
    return `[${type} with children]`;
  }

  return `[${type}]`;
}

export function formatBlockSummary(block: Record<string, unknown>): Record<string, unknown> {
  return {
    id: block.id,
    type: block.type,
    has_children: block.has_children,
    content: formatBlockContent(block),
  };
}

export function formatUserSummary(user: Record<string, unknown>): Record<string, unknown> {
  return { id: user.id, name: user.name, type: user.type, avatar_url: user.avatar_url };
}

// ---------------------------------------------------------------------------
// Rich text builders for creating content
// ---------------------------------------------------------------------------

export function buildRichText(text: string): unknown[] {
  return [{ type: 'text', text: { content: text } }];
}

export function buildParagraphBlock(text: string): Record<string, unknown> {
  return { object: 'block', type: 'paragraph', paragraph: { rich_text: buildRichText(text) } };
}
