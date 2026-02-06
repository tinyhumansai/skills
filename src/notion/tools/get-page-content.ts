// Tool: notion-get-page-content
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
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
      const { notionFetch, formatBlockSummary } = n();
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
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
