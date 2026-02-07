// Tool: notion-get-block
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
      const { formatBlockSummary } = n();
      const blockId = (args.block_id as string) || '';
      if (!blockId) {
        return JSON.stringify({ error: 'block_id is required' });
      }

      const block = getApi().getBlock(blockId);

      return JSON.stringify({
        ...formatBlockSummary(block as Record<string, unknown>),
        raw: block,
      });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
