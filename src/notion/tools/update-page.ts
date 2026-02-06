// Tool: notion-update-page
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const updatePageTool: ToolDefinition = {
  name: 'notion-update-page',
  description:
    "Update a page's properties. Can update title and other properties. " +
    'Use notion-append-text to add content blocks.',
  input_schema: {
    type: 'object',
    properties: {
      page_id: { type: 'string', description: 'The page ID to update' },
      title: { type: 'string', description: 'New title (optional)' },
      properties: { type: 'string', description: 'JSON string of properties to update' },
      archived: {
        type: 'string',
        enum: ['true', 'false'],
        description: 'Set to true to archive the page',
      },
    },
    required: ['page_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatPageSummary, buildRichText } = n();
      const pageId = (args.page_id as string) || '';
      const title = args.title as string | undefined;
      const propsJson = args.properties as string | undefined;
      const archived = args.archived as string | undefined;

      if (!pageId) {
        return JSON.stringify({ error: 'page_id is required' });
      }

      const body: Record<string, unknown> = {};

      if (title) {
        body.properties = { title: { title: buildRichText(title) } };
      }

      if (propsJson) {
        try {
          const props = JSON.parse(propsJson) as Record<string, unknown>;
          const existingProps = (body.properties || {}) as Record<string, unknown>;
          body.properties = { ...existingProps, ...props };
        } catch {
          return JSON.stringify({ error: 'Invalid properties JSON' });
        }
      }

      if (archived !== undefined) {
        body.archived = archived === 'true';
      }

      if (Object.keys(body).length === 0) {
        return JSON.stringify({ error: 'No updates specified' });
      }

      const page = notionFetch(`/pages/${pageId}`, { method: 'PATCH', body }) as Record<
        string,
        unknown
      >;

      return JSON.stringify({ success: true, page: formatPageSummary(page) });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
