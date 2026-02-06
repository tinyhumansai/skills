// Shared types for wallet skill

export interface WalletAccount {
  index: number;
  chain_type: 'evm' | 'sol';
  address: string;
  label: string;
}

export interface NetworkConfig {
  chain_id: string;
  name: string;
  rpc_url: string;
  chain_type: 'evm' | 'sol';
}

export interface WalletSkillConfig {
  walletAddresses: string[];
  networks: NetworkConfig[];
}

export const DEFAULT_NETWORKS: NetworkConfig[] = [
  { chain_id: '1', name: 'Ethereum Mainnet', rpc_url: 'https://eth.llamarpc.com', chain_type: 'evm' },
  { chain_id: '137', name: 'Polygon', rpc_url: 'https://polygon.llamarpc.com', chain_type: 'evm' },
  { chain_id: '56', name: 'BNB Smart Chain', rpc_url: 'https://bsc.llamarpc.com', chain_type: 'evm' },
  { chain_id: '42161', name: 'Arbitrum One', rpc_url: 'https://arb1.arbitrum.io/rpc', chain_type: 'evm' },
  { chain_id: '10', name: 'Optimism', rpc_url: 'https://mainnet.optimism.io', chain_type: 'evm' },
  { chain_id: '43114', name: 'Avalanche C-Chain', rpc_url: 'https://avalanche.public-rpc.com', chain_type: 'evm' },
  { chain_id: '8453', name: 'Base', rpc_url: 'https://mainnet.base.org', chain_type: 'evm' },
  { chain_id: 'mainnet-beta', name: 'Solana Mainnet', rpc_url: 'https://api.mainnet-beta.solana.com', chain_type: 'sol' },
  { chain_id: 'devnet', name: 'Solana Devnet', rpc_url: 'https://api.devnet.solana.com', chain_type: 'sol' },
];
