// Tool: notion-update-block
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const updateBlockTool: ToolDefinition = {
  name: 'notion-update-block',
  description: "Update a block's content. The structure depends on the block type.",
  input_schema: {
    type: 'object',
    properties: {
      block_id: { type: 'string', description: 'The block ID to update' },
      content: {
        type: 'string',
        description:
          'JSON string of the block type content. Example for paragraph: {"paragraph":{"rich_text":[{"text":{"content":"Updated text"}}]}}',
      },
      archived: {
        type: 'string',
        enum: ['true', 'false'],
        description: 'Set to true to archive the block',
      },
    },
    required: ['block_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatBlockSummary } = n();
      const blockId = (args.block_id as string) || '';
      const contentJson = args.content as string | undefined;
      const archived = args.archived as string | undefined;

      if (!blockId) {
        return JSON.stringify({ error: 'block_id is required' });
      }

      const body: Record<string, unknown> = {};

      if (contentJson) {
        try {
          const content = JSON.parse(contentJson);
          Object.assign(body, content);
        } catch {
          return JSON.stringify({ error: 'Invalid content JSON' });
        }
      }

      if (archived !== undefined) {
        body.archived = archived === 'true';
      }

      if (Object.keys(body).length === 0) {
        return JSON.stringify({ error: 'No updates specified' });
      }

      const block = notionFetch(`/blocks/${blockId}`, { method: 'PATCH', body }) as Record<
        string,
        unknown
      >;

      return JSON.stringify({ success: true, block: formatBlockSummary(block) });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
