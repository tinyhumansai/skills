// Tool: notion-list-comments
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const listCommentsTool: ToolDefinition = {
  name: 'notion-list-comments',
  description: 'List comments on a block or page.',
  input_schema: {
    type: 'object',
    properties: {
      block_id: { type: 'string', description: 'Block or page ID to get comments for' },
      page_size: { type: 'number', description: 'Number of results (default 20, max 100)' },
    },
    required: ['block_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatRichText } = n();
      const blockId = (args.block_id as string) || '';
      const pageSize = Math.min((args.page_size as number) || 20, 100);

      if (!blockId) {
        return JSON.stringify({ error: 'block_id is required' });
      }

      const result = notionFetch(`/comments?block_id=${blockId}&page_size=${pageSize}`) as {
        results: Record<string, unknown>[];
        has_more: boolean;
      };

      const comments = result.results.map(comment => ({
        id: comment.id,
        discussion_id: comment.discussion_id,
        created_time: comment.created_time,
        created_by: comment.created_by,
        text: formatRichText(comment.rich_text as unknown[]),
      }));

      return JSON.stringify({ count: comments.length, has_more: result.has_more, comments });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
