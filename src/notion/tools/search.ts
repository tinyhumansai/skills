// Tool: notion-search
import type { NotionApi } from '../api/index';
import type { NotionGlobals } from '../types';

// Resolve from globalThis at runtime (esbuild IIFE breaks module imports)
const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};
const getApi = (): NotionApi => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionApi === 'object') {
    return (g.exports as Record<string, unknown>).notionApi as NotionApi;
  }
  return (g as Record<string, unknown>).notionApi as NotionApi;
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
      const { formatPageSummary, formatDatabaseSummary } = n();
      const query = ((args.query as string) || '').trim();
      const filter = args.filter as string | undefined;
      const pageSize = Math.min((args.page_size as number) || 20, 100);

      const body: Record<string, unknown> = { page_size: pageSize };
      if (query) body.query = query;
      if (filter)
        body.filter = { property: 'object', value: filter === 'database' ? 'data_source' : filter };

      const result = getApi().search(body);

      const formatted = result.results.map((item: Record<string, unknown>) => {
        const obj = item;
        if (obj.object === 'page') {
          return { object: 'page', ...formatPageSummary(obj) };
        }
        if (obj.object === 'database' || obj.object === 'data_source') {
          return { object: 'data_source', ...formatDatabaseSummary(obj) };
        }
        return { object: obj.object, id: obj.id };
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
