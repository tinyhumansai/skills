// Raw GitHub API tool (1 tool)
import { ghFetch } from '../api';
import { optString, reqString, truncate } from '../helpers';

export const ghApiTool: ToolDefinition = {
  name: 'gh-api',
  description:
    'Make a raw GitHub REST API request. Use this for any endpoint not covered by the other tools',
  input_schema: {
    type: 'object',
    properties: {
      endpoint: {
        type: 'string',
        description: "API endpoint path (e.g. '/repos/owner/repo/branches')",
      },
      method: {
        type: 'string',
        description: 'HTTP method',
        enum: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
      },
      body: { type: 'object', description: 'Request body (for POST/PUT/PATCH)' },
    },
    required: ['endpoint'],
  },
  async execute(args: Record<string, unknown>): Promise<string> {
    try {
      let endpoint = reqString(args, 'endpoint');
      const method = (optString(args, 'method') || 'GET').toUpperCase();
      const body = args.body;

      if (!endpoint.startsWith('/')) endpoint = '/' + endpoint;

      const response = await ghFetch(endpoint, {
        method,
        body:
          body && (method === 'POST' || method === 'PUT' || method === 'PATCH') ? body : undefined,
      });

      if (response.data === null) return JSON.stringify({ result: '(no content)' });
      return JSON.stringify({ result: truncate(JSON.stringify(response.data, null, 2)) });
    } catch (e) {
      return JSON.stringify({ error: String(e) });
    }
  },
};

export const apiTools: ToolDefinition[] = [ghApiTool];
