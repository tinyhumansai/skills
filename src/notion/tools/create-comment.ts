// Tool: notion-create-comment
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const createCommentTool: ToolDefinition = {
  name: 'notion-create-comment',
  description:
    'Create a comment on a page or in a discussion thread. ' +
    'Must specify either page_id (for new discussion) or discussion_id (to reply).',
  input_schema: {
    type: 'object',
    properties: {
      page_id: { type: 'string', description: 'Page ID to start a new discussion on' },
      discussion_id: {
        type: 'string',
        description: 'Discussion ID to reply to an existing thread',
      },
      text: { type: 'string', description: 'Comment text content' },
    },
    required: ['text'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatRichText, buildRichText } = n();
      const pageId = args.page_id as string | undefined;
      const discussionId = args.discussion_id as string | undefined;
      const text = (args.text as string) || '';

      if (!pageId && !discussionId) {
        return JSON.stringify({ error: 'Either page_id or discussion_id is required' });
      }
      if (!text) {
        return JSON.stringify({ error: 'text is required' });
      }

      const body: Record<string, unknown> = { rich_text: buildRichText(text) };

      if (discussionId) {
        body.discussion_id = discussionId;
      } else if (pageId) {
        body.parent = { page_id: pageId };
      }

      const comment = notionFetch('/comments', { method: 'POST', body }) as Record<string, unknown>;

      return JSON.stringify({
        success: true,
        comment: {
          id: comment.id,
          discussion_id: comment.discussion_id,
          created_time: comment.created_time,
          text: formatRichText(comment.rich_text as unknown[]),
        },
      });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
