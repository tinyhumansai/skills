// Tool: notion-list-all-databases
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const listAllDatabasesTool: ToolDefinition = {
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
      const { notionFetch, formatDatabaseSummary } = n();
      const pageSize = Math.min((args.page_size as number) || 20, 100);

      const result = notionFetch('/search', {
        method: 'POST',
        body: { filter: { property: 'object', value: 'database' }, page_size: pageSize },
      }) as { results: Record<string, unknown>[]; has_more: boolean };

      const databases = result.results.map(formatDatabaseSummary);

      return JSON.stringify({ count: databases.length, has_more: result.has_more, databases });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
