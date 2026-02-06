// Tool: notion-create-database
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const createDatabaseTool: ToolDefinition = {
  name: 'notion-create-database',
  description: 'Create a new database in Notion. Must specify parent page and property schema.',
  input_schema: {
    type: 'object',
    properties: {
      parent_page_id: {
        type: 'string',
        description: 'Parent page ID where the database will be created',
      },
      title: { type: 'string', description: 'Database title' },
      properties: {
        type: 'string',
        description:
          'JSON string of properties schema. Example: {"Name":{"title":{}},"Status":{"select":{"options":[{"name":"Todo"},{"name":"Done"}]}}}',
      },
    },
    required: ['parent_page_id', 'title'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatDatabaseSummary, buildRichText } = n();
      const parentId = (args.parent_page_id as string) || '';
      const title = (args.title as string) || '';
      const propsJson = args.properties as string | undefined;

      if (!parentId) {
        return JSON.stringify({ error: 'parent_page_id is required' });
      }
      if (!title) {
        return JSON.stringify({ error: 'title is required' });
      }

      let properties: Record<string, unknown> = { Name: { title: {} } };

      if (propsJson) {
        try {
          properties = JSON.parse(propsJson);
        } catch {
          return JSON.stringify({ error: 'Invalid properties JSON' });
        }
      }

      const body = { parent: { page_id: parentId }, title: buildRichText(title), properties };

      const dbResult = notionFetch('/databases', { method: 'POST', body }) as Record<
        string,
        unknown
      >;

      return JSON.stringify({ success: true, database: formatDatabaseSummary(dbResult) });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
