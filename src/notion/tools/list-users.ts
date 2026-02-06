// Tool: notion-list-users
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const listUsersTool: ToolDefinition = {
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
      const { notionFetch, formatUserSummary } = n();
      const pageSize = Math.min((args.page_size as number) || 20, 100);

      const result = notionFetch(`/users?page_size=${pageSize}`) as {
        results: Record<string, unknown>[];
        has_more: boolean;
      };

      const users = result.results.map(formatUserSummary);

      return JSON.stringify({ count: users.length, has_more: result.has_more, users });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
