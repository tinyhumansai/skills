/** list-peers tool — discover other skills via skills.list() */
export const listPeersTool: ToolDefinition = {
  name: 'list-peers',
  description: 'List all registered skills in the runtime.',
  input_schema: {
    type: 'object',
    properties: {},
  },
  execute(_args: Record<string, unknown>): string {
    const peers = skills.list();
    return JSON.stringify({ count: peers.length, skills: peers });
  },
};
