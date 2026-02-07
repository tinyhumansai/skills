/**
 * wallet skill — Web3 wallet connector using wallet address from the frontend.
 *
 * The frontend derives the EVM wallet address from the user's mnemonic (same as encryption)
 * and passes it via load params. This skill uses that address for list_wallets, get_balance, etc.
 */
import './skill-state';
import { getBalanceTool } from './tools/get-balance';
import { listNetworksTool } from './tools/list-networks';
import { listWalletsTool } from './tools/list-wallets';
import { DEFAULT_NETWORKS, type NetworkConfig } from './types';

const tools = [listWalletsTool, listNetworksTool, getBalanceTool];

function getState(): import('./skill-state').WalletSkillState {
  return (globalThis as any).getState();
}

function init(): void {
  const s = getState();
  const saved = store.get('config') as {
    walletAddresses?: string[];
    networks?: NetworkConfig[];
  } | null;
  if (saved?.walletAddresses?.length) {
    s.config.walletAddresses = saved.walletAddresses;
  }
  if (saved?.networks?.length) {
    s.config.networks = saved.networks;
  }
  // Ensure at least Ethereum Mainnet is always available
  if (s.config.networks.length === 0) {
    const networks = Array.isArray(DEFAULT_NETWORKS) ? DEFAULT_NETWORKS : [];
    const eth = networks.find(n => n.chain_id === '1');
    if (eth) {
      s.config.networks = [eth];
    }
  }
}

function start(): void {
  const s = getState();
  s.isRunning = true;
  state.setPartial({
    connection_status: 'connected',
    status: 'running',
    walletCount: s.config.walletAddresses.length,
    networkCount: s.config.networks.length,
  });
}

function stop(): void {
  const s = getState();
  s.isRunning = false;
  state.setPartial({ connection_status: 'disconnected', status: 'stopped' });
}

/**
 * Called when the frontend sends load params (e.g. wallet address derived from mnemonic).
 * params.walletAddress is the primary EVM address from the app.
 */
function onLoad(params: { walletAddress?: string; walletAddresses?: string[] }): void {
  const s = getState();
  if (params.walletAddress) {
    if (!s.config.walletAddresses.includes(params.walletAddress)) {
      s.config.walletAddresses = [params.walletAddress];
      store.set('config', s.config);
    }
  }
  if (params.walletAddresses?.length) {
    s.config.walletAddresses = params.walletAddresses;
    store.set('config', s.config);
  }
  state.setPartial({ walletCount: s.config.walletAddresses.length });
}

function onSetupStart(): SetupStartResult {
  // Guard against unexpected bundling/runtime issues where DEFAULT_NETWORKS
  // might not be initialized as an array in the JS runtime.
  const networks = Array.isArray(DEFAULT_NETWORKS) ? DEFAULT_NETWORKS : [];
  const evmOptions = networks.map(n => ({ label: n.name, value: n.chain_id }));

  return {
    step: {
      id: 'networks',
      title: 'Select Networks',
      description:
        'Choose which blockchain networks to enable for balance checks. Your wallet address from the app will be used.',
      fields: [
        {
          name: 'evm_networks',
          type: 'multiselect',
          label: 'EVM Networks',
          description: 'Select EVM networks (Ethereum, Polygon, BSC, etc.)',
          required: false,
          options: evmOptions,
        },
      ],
    },
  };
}

function onSetupSubmit(args: {
  stepId: string;
  values: Record<string, unknown>;
}): SetupSubmitResult {
  const s = getState();

  if (args.stepId === 'networks') {
    const networks = Array.isArray(DEFAULT_NETWORKS) ? DEFAULT_NETWORKS : [];
    const evmSelected = (args.values.evm_networks as string[]) || [];
    s.config.networks = networks.filter(n => evmSelected.includes(n.chain_id));
    if (s.config.networks.length === 0) {
      s.config.networks = networks.slice(0, 3);
    }
    store.set('config', s.config);
    return { status: 'complete' };
  }

  return { status: 'error', errors: [{ field: '', message: `Unknown step: ${args.stepId}` }] };
}

function onSetupCancel(): void {
  // No transient state to clear
}

const _g = globalThis as Record<string, unknown>;
_g.init = init;
_g.start = start;
_g.stop = stop;
_g.onLoad = onLoad;
_g.onSetupStart = onSetupStart;
_g.onSetupSubmit = onSetupSubmit;
_g.onSetupCancel = onSetupCancel;
_g.tools = tools;
// getState is already on globalThis from skill-state (needed for bundle compatibility)
