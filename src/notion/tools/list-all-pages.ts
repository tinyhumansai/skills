// Tool: notion-list-all-pages
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const listAllPagesTool: ToolDefinition = {
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
      const { notionFetch, formatPageSummary } = n();
      const pageSize = Math.min((args.page_size as number) || 20, 100);

      const result = notionFetch('/search', {
        method: 'POST',
        body: { filter: { property: 'object', value: 'page' }, page_size: pageSize },
      }) as { results: Record<string, unknown>[]; has_more: boolean };

      const pages = result.results.map(formatPageSummary);

      return JSON.stringify({ count: pages.length, has_more: result.has_more, pages });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
