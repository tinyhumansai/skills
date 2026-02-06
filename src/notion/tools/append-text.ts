// Tool: notion-append-text
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const appendTextTool: ToolDefinition = {
  name: 'notion-append-text',
  description:
    'Append text content to a page or block. Creates paragraph blocks with the given text.',
  input_schema: {
    type: 'object',
    properties: {
      block_id: { type: 'string', description: 'The page or block ID to append to' },
      text: { type: 'string', description: 'Text content to append' },
    },
    required: ['block_id', 'text'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatBlockSummary, buildParagraphBlock } = n();
      const blockId = (args.block_id as string) || '';
      const text = (args.text as string) || '';

      if (!blockId) {
        return JSON.stringify({ error: 'block_id is required' });
      }
      if (!text) {
        return JSON.stringify({ error: 'text is required' });
      }

      const paragraphs = text.split('\n').filter(p => p.trim());
      const children = paragraphs.map(buildParagraphBlock);

      const result = notionFetch(`/blocks/${blockId}/children`, {
        method: 'PATCH',
        body: { children },
      }) as { results: Record<string, unknown>[] };

      return JSON.stringify({
        success: true,
        blocks_added: result.results.length,
        blocks: result.results.map(formatBlockSummary),
      });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
