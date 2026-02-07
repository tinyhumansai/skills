// Tool: list_wallets — list wallet addresses from frontend (derived from mnemonic)
export const listWalletsTool = {
  name: 'list_wallets',
  description:
    'List all wallet addresses configured for this skill (derived from your mnemonic in the app).',
  input_schema: { type: 'object', properties: {} },
  execute(): string {
    const s = (globalThis as any).getState() as { config: { walletAddresses: string[] } };
    const wallets = s.config.walletAddresses.map((address: string, index: number) => ({
      index,
      chain_type: 'evm',
      address,
      label: `Wallet ${index}`,
    }));
    return JSON.stringify({ wallets }, null, 2);
  },
};
