// Tool: notion-update-database
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

export const updateDatabaseTool: ToolDefinition = {
  name: 'notion-update-database',
  description: "Update a database's title or properties schema.",
  input_schema: {
    type: 'object',
    properties: {
      database_id: { type: 'string', description: 'The database ID to update' },
      title: { type: 'string', description: 'New title (optional)' },
      properties: { type: 'string', description: 'JSON string of properties to add or update' },
    },
    required: ['database_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { formatDatabaseSummary, buildRichText } = n();
      const databaseId = (args.database_id as string) || '';
      const title = args.title as string | undefined;
      const propsJson = args.properties as string | undefined;

      if (!databaseId) {
        return JSON.stringify({ error: 'database_id is required' });
      }

      const body: Record<string, unknown> = {};

      if (title) {
        body.title = buildRichText(title);
      }

      if (propsJson) {
        try {
          body.properties = JSON.parse(propsJson);
        } catch {
          return JSON.stringify({ error: 'Invalid properties JSON' });
        }
      }

      if (Object.keys(body).length === 0) {
        return JSON.stringify({ error: 'No updates specified' });
      }

      const dbResult = getApi().updateDatabase(databaseId, body);

      return JSON.stringify({
        success: true,
        database: formatDatabaseSummary(dbResult as Record<string, unknown>),
      });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
