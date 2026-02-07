// Tool: notion-list-all-databases
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

export const listAllDatabasesTool: ToolDefinition = {
  name: 'notion-list-all-databases',
  description: 'List all databases in the workspace that the integration has access to.',
  input_schema: {
    type: 'object',
    properties: {
      page_size: { type: 'number', description: 'Number of results (default 20, max 100)' },
    },
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { formatDatabaseSummary } = n();
      const pageSize = Math.min((args.page_size as number) || 20, 100);

      const result = getApi().listAllDatabases(pageSize);

      const databases = result.results.map((item: Record<string, unknown>) =>
        formatDatabaseSummary(item)
      );
      return JSON.stringify({ count: databases.length, has_more: result.has_more, databases });
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
