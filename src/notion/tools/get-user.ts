// Tool: notion-get-user
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

export const getUserTool: ToolDefinition = {
  name: 'notion-get-user',
  description: 'Get a user by their ID.',
  input_schema: {
    type: 'object',
    properties: { user_id: { type: 'string', description: 'The user ID' } },
    required: ['user_id'],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const { formatUserSummary } = n();
      const userId = (args.user_id as string) || '';
      if (!userId) {
        return JSON.stringify({ error: 'user_id is required' });
      }

      const user = getApi().getUser(userId);

      return JSON.stringify(formatUserSummary(user as Record<string, unknown>));
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
