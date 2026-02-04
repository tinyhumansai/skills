// Tool: update-server-url
// Change the monitored server URL at runtime.

// Import ensures state is initialized
import '../skill-state';

export const updateServerUrlTool: ToolDefinition = {
  name: 'update-server-url',
  description: 'Change the monitored server URL at runtime.',
  input_schema: {
    type: 'object',
    properties: { url: { type: 'string', description: 'New server URL to monitor' } },
    required: ['url'],
  },
  execute(args: Record<string, unknown>): string {
    const url = ((args.url as string) ?? '').trim();
    if (!url || !url.startsWith('http')) {
      return JSON.stringify({ error: 'Invalid URL — must start with http:// or https://' });
    }

    const s = globalThis.getSkillState();
    const oldUrl = s.config.serverUrl;
    s.config.serverUrl = url;
    store.set('config', s.config);

    console.log(`[server-ping] Server URL changed: ${oldUrl} -> ${url}`);
    // publishState is exposed on globalThis by the main skill module
    (globalThis as { publishState?: () => void }).publishState?.();

    return JSON.stringify({ success: true, oldUrl, newUrl: url });
  },
};
