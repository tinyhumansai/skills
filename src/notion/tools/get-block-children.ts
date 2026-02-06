// Tool: notion-get-block-children
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const getBlockChildrenTool: ToolDefinition = {
  name: 'notion-get-block-children',
  description: 'Get the children blocks of a block or page.',
  input_schema: {
    type: 'object',
    properties: {
      block_id: { type: 'string', description: 'The parent block or page ID' },
      page_size: { type: 'number', description: 'Number of blocks (default 50, max 100)' },
    },
    required: ['block_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatBlockSummary } = n();
      const blockId = (args.block_id as string) || '';
      const pageSize = Math.min((args.page_size as number) || 50, 100);

      if (!blockId) {
        return JSON.stringify({ error: 'block_id is required' });
      }

      const result = notionFetch(`/blocks/${blockId}/children?page_size=${pageSize}`) as {
        results: Record<string, unknown>[];
        has_more: boolean;
      };

      return JSON.stringify({
        parent_id: blockId,
        count: result.results.length,
        has_more: result.has_more,
        children: result.results.map(formatBlockSummary),
      });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
