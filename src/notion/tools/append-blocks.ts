// Tool: notion-append-blocks
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

export const appendBlocksTool: ToolDefinition = {
  name: 'notion-append-blocks',
  description: 'Append child blocks to a page or block. Supports various block types.',
  input_schema: {
    type: 'object',
    properties: {
      block_id: { type: 'string', description: 'The parent page or block ID' },
      blocks: {
        type: 'string',
        description:
          'JSON string of blocks array. Example: [{"type":"paragraph","paragraph":{"rich_text":[{"text":{"content":"Hello"}}]}}]',
      },
    },
    required: ['block_id', 'blocks'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { formatBlockSummary } = n();
      const blockId = (args.block_id as string) || '';
      const blocksJson = (args.blocks as string) || '';

      if (!blockId) {
        return JSON.stringify({ error: 'block_id is required' });
      }
      if (!blocksJson) {
        return JSON.stringify({ error: 'blocks is required' });
      }

      let children: unknown[];
      try {
        children = JSON.parse(blocksJson);
      } catch {
        return JSON.stringify({ error: 'Invalid blocks JSON' });
      }

      if (!Array.isArray(children) || children.length === 0) {
        return JSON.stringify({ error: 'blocks must be a non-empty array' });
      }

      const result = getApi().appendBlockChildren(blockId, children);

      return JSON.stringify({
        success: true,
        blocks_added: result.results.length,
        blocks: result.results.map((b: Record<string, unknown>) => formatBlockSummary(b)),
      });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
