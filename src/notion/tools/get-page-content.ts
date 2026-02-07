// Tool: notion-get-page-content
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

export const getPageContentTool: ToolDefinition = {
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
      const { formatBlockSummary } = n();
      const api = getApi();
      const pageId = (args.page_id as string) || '';
      const recursive = args.recursive === 'true';
      const pageSize = Math.min((args.page_size as number) || 50, 100);

      if (!pageId) {
        return JSON.stringify({ error: 'page_id is required' });
      }

      const result = api.getPageContent(pageId, pageSize);

      const blocks = result.results.map((block: Record<string, unknown>) => {
        const summary = formatBlockSummary(block);

        if (recursive && block.has_children) {
          try {
            const children = api.getBlockChildren(block.id as string, 50);
            return {
              ...summary,
              children: children.results.map((c: Record<string, unknown>) => formatBlockSummary(c)),
            };
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
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
