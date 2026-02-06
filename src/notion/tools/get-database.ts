// Tool: notion-get-database
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
};

export const getDatabaseTool: ToolDefinition = {
  name: 'notion-get-database',
  description: "Get a database's schema and metadata. Shows all properties and their types.",
  input_schema: {
    type: 'object',
    properties: { database_id: { type: 'string', description: 'The database ID' } },
    required: ['database_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { notionFetch, formatDatabaseSummary } = n();
      const databaseId = (args.database_id as string) || '';
      if (!databaseId) {
        return JSON.stringify({ error: 'database_id is required' });
      }

      const dbResult = notionFetch(`/databases/${databaseId}`) as Record<string, unknown>;

      const props = dbResult.properties as Record<string, unknown>;
      const schema: Record<string, unknown> = {};
      for (const [name, prop] of Object.entries(props)) {
        const propData = prop as Record<string, unknown>;
        schema[name] = { type: propData.type, id: propData.id };
      }

      return JSON.stringify({ ...formatDatabaseSummary(dbResult), schema });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
