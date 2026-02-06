// Tool: notion-delete-block
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const deleteBlockTool: ToolDefinition = {
  name: 'notion-delete-block',
  description: 'Delete a block. This permanently removes the block from Notion.',
  input_schema: {
    type: 'object',
    properties: { block_id: { type: 'string', description: 'The block ID to delete' } },
    required: ['block_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch } = n();
      const blockId = (args.block_id as string) || '';
      if (!blockId) {
        return JSON.stringify({ error: 'block_id is required' });
      }

      notionFetch(`/blocks/${blockId}`, { method: 'DELETE' });

      return JSON.stringify({ success: true, message: 'Block deleted', block_id: blockId });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
