/** fetch-data tool — makes an HTTP request to the configured server URL */

export const fetchDataTool: ToolDefinition = {
  name: 'fetch-data',
  description: 'Fetch data from the configured server URL. Returns the response status and body.',
  input_schema: {
    type: 'object',
    properties: {
      endpoint: {
        type: 'string',
        description: 'Optional path to append to the server URL (e.g., "/health")',
      },
    },
  },
  execute(args: Record<string, unknown>): string {
    const s = (globalThis as any).getSkillState();
    const endpoint = (args.endpoint as string) || '';
    const url = s.config.serverUrl + endpoint;

    if (!s.config.serverUrl) return JSON.stringify({ error: 'Server URL not configured' });

    try {
      const response = net.fetch(url, {
        method: 'GET',
        headers: { Authorization: `Bearer ${s.config.apiKey}`, 'Content-Type': 'application/json' },
        timeout: 10000,
      });

      s.fetchCount++;
      s.lastFetchTime = new Date().toISOString();

      return JSON.stringify({ status: response.status, body: response.body });
    } catch (e) {
      s.errorCount++;
      return JSON.stringify({ error: String(e) });
    }
  },
};
