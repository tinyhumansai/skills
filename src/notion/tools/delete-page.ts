// Tool: notion-delete-page
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const deletePageTool: ToolDefinition = {
  name: 'notion-delete-page',
  description: "Delete (archive) a page. Archived pages can be restored from Notion's trash.",
  input_schema: {
    type: 'object',
    properties: { page_id: { type: 'string', description: 'The page ID to delete/archive' } },
    required: ['page_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatPageSummary } = n();
      const pageId = (args.page_id as string) || '';
      if (!pageId) {
        return JSON.stringify({ error: 'page_id is required' });
      }

      const page = notionFetch(`/pages/${pageId}`, {
        method: 'PATCH',
        body: { archived: true },
      }) as Record<string, unknown>;

      return JSON.stringify({
        success: true,
        message: 'Page archived',
        page: formatPageSummary(page),
      });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
