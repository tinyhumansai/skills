// Notion API helpers and formatting functions

// ---------------------------------------------------------------------------
// Notion API helpers
// ---------------------------------------------------------------------------

/** Max retries on 429 rate-limit responses. */
const MAX_RETRIES = 3;

/** Default backoff in ms when Retry-After header is absent. */
const DEFAULT_BACKOFF_MS = 5_000;

/** Async sleep for backoff waits. */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export async function notionFetch<T>(
  endpoint: string,
  options: { method?: string; body?: unknown } = {}
): Promise<T> {
  const credential = oauth.getCredential();
  if (!credential) throw new Error('Notion not connected. Please complete setup first.');

  const method = options.method || 'GET';
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const useAccessToken = !!credential.accessToken;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    let response: { status: number; headers: Record<string, string>; body: string };

    if (useAccessToken) {
      // Prefer direct Notion API call with access token provided by the frontend,
      // mirroring the Gmail skill pattern.
      const url = `https://api.notion.com/v1${path}`;
      response = await net.fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${credential.accessToken as string}`,
          'Content-Type': 'application/json',
          'Notion-Version': '2022-06-28',
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
        timeout: 30,
      });
    } else {
      // Fallback: use server-side OAuth proxy (original behavior)
      response = await oauth.fetch(`/v1${path}`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: options.body ? JSON.stringify(options.body) : undefined,
        timeout: 30,
      });
    }

    // -- 429 Rate Limit: back off and retry ----------------------------------
    if (response.status === 429 && attempt < MAX_RETRIES) {
      const retryAfter = response.headers['retry-after'];
      const waitMs = retryAfter
        ? parseInt(retryAfter, 10) * 1000
        : DEFAULT_BACKOFF_MS * (attempt + 1);
      await sleep(waitMs);
      continue;
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
      console.error('[notion][helpers] notionFetch error body:', errorBody);
      throw new Error(message);
    }

    const parsed = JSON.parse(response.body as string) as T;
    return parsed;
  }

  // Exhausted retries (only reachable after repeated 429s)
  throw new Error('Notion API error: 429 — rate limit exceeded after retries');
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
  // Default to top-level user fields
  let id = user.id as string;
  let name = user.name as string | undefined;
  let email: string | undefined;
  let avatarUrl = user.avatar_url as string | undefined;
  let userType = user.type as string | undefined;

  // For bot-type users, drill into bot.owner.user.person to get the human owner info
  if (userType === 'bot') {
    const bot = user.bot as Record<string, unknown> | undefined;
    const owner = bot?.owner as Record<string, unknown> | undefined;
    const ownerUser = owner?.user as Record<string, unknown> | undefined;
    const ownerPerson = ownerUser?.person as Record<string, unknown> | undefined;

    if (ownerUser) {
      id = (ownerUser.id as string) || id;
      name = (ownerUser.name as string) || name;
      avatarUrl = (ownerUser.avatar_url as string) || avatarUrl;
      userType = (ownerUser.type as string) || userType;
    }
    if (ownerPerson) {
      email = (ownerPerson.email as string) || email;
    }
  } else {
    const person = user.person as Record<string, unknown> | undefined;
    email = (person?.email as string) || (user.email as string | undefined);
  }

  return {
    id,
    name: name ?? null,
    email: email ?? null,
    type: userType ?? null,
    avatar_url: avatarUrl ?? null,
  };
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

// ---------------------------------------------------------------------------
// Block tree text extraction for content sync
// ---------------------------------------------------------------------------

/**
 * Recursively fetch block children and extract plain text content.
 * Used by the sync engine to populate page content_text.
 */
export async function fetchBlockTreeText(blockId: string, maxDepth: number = 2): Promise<string> {
  if (maxDepth < 0) return '';

  const lines: string[] = [];
  let startCursor: string | undefined;
  let hasMore = true;

  while (hasMore) {
    const endpoint = `/blocks/${blockId}/children?page_size=100${startCursor ? `&start_cursor=${startCursor}` : ''}`;

    let result: { results: Record<string, unknown>[]; has_more: boolean; next_cursor?: string };
    try {
      result = (await notionFetch(endpoint)) as typeof result;
    } catch {
      // If we can't fetch children (permissions, deleted, etc.), skip
      break;
    }

    for (const block of result.results) {
      const text = formatBlockContent(block);
      // Only include blocks that have meaningful text
      if (text && !text.startsWith('[') && !text.endsWith(']')) {
        lines.push(text);
      } else if (text && text !== `[${block.type as string}]`) {
        // Include non-empty typed blocks (e.g. "[empty paragraph]" is skipped)
        const cleaned = text.replace(/^\[empty .*\]$/, '').trim();
        if (cleaned) lines.push(cleaned);
      }

      // Recurse into children if the block has them and we have depth budget
      if (block.has_children && maxDepth > 0) {
        const childText = await fetchBlockTreeText(block.id as string, maxDepth - 1);
        if (childText) lines.push(childText);
      }
    }

    hasMore = result.has_more;
    startCursor = result.next_cursor as string | undefined;
  }

  return lines.join('\n');
}
