// Tool: get_balance — get balance for a wallet address on a network via RPC
function evmGetBalance(rpcUrl: string, address: string): string {
  const body = JSON.stringify({
    jsonrpc: '2.0',
    id: 1,
    method: 'eth_getBalance',
    params: [address, 'latest'],
  });
  const response = net.fetch(rpcUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    timeout: 10000,
  });
  if (response.status !== 200) {
    return JSON.stringify({
      error: `RPC request failed: status ${response.status}`,
      address,
      rpc_url: rpcUrl,
    });
  }
  let data: { result?: string; error?: { message: string } };
  try {
    data = JSON.parse(response.body);
  } catch {
    return JSON.stringify({ error: 'Invalid RPC response', address, rpc_url: rpcUrl });
  }
  if (data.error) {
    return JSON.stringify({ error: data.error.message, address, rpc_url: rpcUrl });
  }
  const hexBalance = data.result || '0x0';
  const wei = BigInt(hexBalance);
  const eth = Number(wei) / 1e18;
  return JSON.stringify(
    { address, balance_wei: hexBalance, balance_eth: eth.toFixed(18), symbol: 'ETH' },
    null,
    2
  );
}

export const getBalanceTool = {
  name: 'get_balance',
  description:
    'Get the balance of a wallet address on a specific network. Use list_wallets for addresses and list_networks for chain_id.',
  input_schema: {
    type: 'object',
    properties: {
      address: { type: 'string', description: 'Wallet address (0x...) to check' },
      chain_id: { type: 'string', description: 'Chain ID (e.g. 1 for Ethereum, 137 for Polygon)' },
      chain_type: { type: 'string', enum: ['evm'], description: 'Chain type', default: 'evm' },
    },
    required: ['address', 'chain_id'],
  },
  execute(args: Record<string, unknown>): string {
    const s = (globalThis as any).getState() as {
      config: { networks: Array<{ chain_id: string; chain_type: string; rpc_url: string }> };
    };
    const address = (args.address as string) || '';
    const chainId = (args.chain_id as string) || '';
    if (!address) return JSON.stringify({ error: 'Missing required parameter: address' });
    if (!chainId) return JSON.stringify({ error: 'Missing required parameter: chain_id' });

    const network = s.config.networks.find(
      (n: { chain_id: string; chain_type: string }) =>
        n.chain_id === chainId && n.chain_type === 'evm'
    );
    if (!network) {
      return JSON.stringify({
        error: `Network not found for chain_id=${chainId}. Run list_networks to see configured networks.`,
      });
    }

    return evmGetBalance(network.rpc_url, address);
  },
};
