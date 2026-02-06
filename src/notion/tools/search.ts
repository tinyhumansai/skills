// Tool: notion-search
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const searchTool: ToolDefinition = {
  name: 'notion-search',
  description:
    'Search for pages and databases in your Notion workspace. ' +
    'Can filter by type (page or database) and returns matching results.',
  input_schema: {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'Search query (optional, returns recent if empty)' },
      filter: { type: 'string', enum: ['page', 'database'], description: 'Filter results by type' },
      page_size: {
        type: 'number',
        description: 'Number of results to return (default 20, max 100)',
      },
    },
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatPageSummary, formatDatabaseSummary } = n();
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
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
