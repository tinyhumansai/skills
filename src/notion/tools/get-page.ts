// Tool: notion-get-page
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const getPageTool: ToolDefinition = {
  name: 'notion-get-page',
  description:
    "Get a page's metadata and properties by its ID. " +
    'Use notion-get-page-content to get the actual content/blocks.',
  input_schema: {
    type: 'object',
    properties: {
      page_id: { type: 'string', description: 'The page ID (UUID format, with or without dashes)' },
    },
    required: ['page_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatPageSummary } = n();
      const pageId = (args.page_id as string) || '';
      if (!pageId) {
        return JSON.stringify({ error: 'page_id is required' });
      }

      const page = notionFetch(`/pages/${pageId}`) as Record<string, unknown>;

      return JSON.stringify({ ...formatPageSummary(page), properties: page.properties });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
