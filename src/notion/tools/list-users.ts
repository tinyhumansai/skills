// Tool: notion-list-users
import { notionApi } from '../api/index';
import { formatApiError, formatUserSummary } from '../helpers';

export const listUsersTool: ToolDefinition = {
  name: 'list-users',
  description: 'List all users in the workspace that the integration can see.',
  input_schema: {
    type: 'object',
    properties: {
      page_size: { type: 'number', description: 'Number of results (default 20, max 100)' },
    },
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      const pageSize = Math.min((args.page_size as number) || 20, 100);

       const result = await notionApi.listUsers(pageSize);

       const users = result.results.map((u: Record<string, unknown>) => formatUserSummary(u));

      return JSON.stringify({ count: users.length, has_more: result.has_more, users });
    } catch (e) {
      return JSON.stringify({ error: formatApiError(e) });
    }
  },
};
