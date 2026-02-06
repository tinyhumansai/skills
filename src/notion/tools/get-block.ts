// Tool: notion-get-block
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const getBlockTool: ToolDefinition = {
  name: 'notion-get-block',
  description: "Get a block by its ID. Returns the block's type and content.",
  input_schema: {
    type: 'object',
    properties: { block_id: { type: 'string', description: 'The block ID' } },
    required: ['block_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatBlockSummary } = n();
      const blockId = (args.block_id as string) || '';
      if (!blockId) {
        return JSON.stringify({ error: 'block_id is required' });
      }

      const block = notionFetch(`/blocks/${blockId}`) as Record<string, unknown>;

      return JSON.stringify({ ...formatBlockSummary(block), raw: block });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
