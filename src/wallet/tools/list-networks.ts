// Tool: list_networks — list configured blockchain networks
export const listNetworksTool = {
  name: 'list_networks',
  description: 'List all configured EVM blockchain networks with RPC endpoints.',
  input_schema: { type: 'object', properties: {} },
  execute(): string {
    const s = (globalThis as any).getState() as {
      config: {
        networks: Array<{ chain_id: string; name: string; rpc_url: string; chain_type: string }>;
      };
    };
    const networks = s.config.networks.map(
      (n: { chain_id: string; name: string; rpc_url: string; chain_type: string }) => ({
        chain_id: n.chain_id,
        name: n.name,
        rpc_url: n.rpc_url,
        chain_type: n.chain_type,
      })
    );
    return JSON.stringify({ networks }, null, 2);
  },
};
