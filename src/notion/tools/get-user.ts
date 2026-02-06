// Tool: notion-get-user
import type { NotionGlobals } from '../types';

const n = (): NotionGlobals => {
  const g = globalThis as unknown as Record<string, unknown>;
  if (g.exports && typeof (g.exports as Record<string, unknown>).notionFetch === 'function') {
    return g.exports as unknown as NotionGlobals;
  }
  return globalThis as unknown as NotionGlobals;
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
      const { notionFetch, formatUserSummary } = n();
      const userId = (args.user_id as string) || '';
      if (!userId) {
        return JSON.stringify({ error: 'user_id is required' });
      }

      const user = notionFetch(`/users/${userId}`) as Record<string, unknown>;

      return JSON.stringify(formatUserSummary(user));
    } catch (e) {
      return JSON.stringify({ error: n().formatApiError(e) });
    }
  },
};
