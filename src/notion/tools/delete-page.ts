// Tool: notion-delete-page
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
      const { formatPageSummary } = n();
      const pageId = (args.page_id as string) || '';
      if (!pageId) {
        return JSON.stringify({ error: 'page_id is required' });
      }

      const page = getApi().archivePage(pageId);

      return JSON.stringify({
        success: true,
        message: 'Page archived',
        page: formatPageSummary(page as Record<string, unknown>),
      });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
