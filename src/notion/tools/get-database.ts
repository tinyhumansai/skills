// Tool: notion-get-database
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
      const { formatDatabaseSummary } = n();
      const api = getApi();
      const databaseId = (args.database_id as string) || '';
      if (!databaseId) {
        return JSON.stringify({ error: 'database_id is required' });
      }

      const dataSourceId = api.resolveDataSourceId(databaseId);
      const dsResult = api.getDataSource(dataSourceId);

      const dsRec = dsResult as Record<string, unknown>;
      const props = dsRec.properties as Record<string, unknown>;
      const schema: Record<string, unknown> = {};
      if (props) {
        for (const [name, prop] of Object.entries(props)) {
          const propData = prop as Record<string, unknown>;
          schema[name] = { type: propData.type, id: propData.id };
        }
      }

      return JSON.stringify({ ...formatDatabaseSummary(dsRec), schema });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
