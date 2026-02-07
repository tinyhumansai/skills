/**
 * test-wallet.ts — Tests for the wallet skill.
 *
 * Covers init, start, stop, onLoad, setup flow (networks), and tools:
 * list_wallets, list_networks, get_balance (with mocked RPC).
 *
 * All globals (describe, it, assert*, setupSkillTest, callTool, getMockState, etc.)
 * are provided by the test harness when run.
 */
const _describe = (globalThis as any).describe as (name: string, fn: () => void) => void;
const _it = (globalThis as any).it as (name: string, fn: () => void) => void;
const _assert = (globalThis as any).assert as (cond: unknown, msg?: string) => void;
const _assertEqual = (globalThis as any).assertEqual as (
  a: unknown,
  b: unknown,
  msg?: string
) => void;
const _assertNotNull = (globalThis as any).assertNotNull as (v: unknown, msg?: string) => void;
const _assertTrue = (globalThis as any).assertTrue as (v: unknown, msg?: string) => void;
const _setup = (globalThis as any).setupSkillTest as (opts?: any) => void;
const _callTool = (globalThis as any).callTool as (name: string, args?: any) => any;
const _getMockState = (globalThis as any).getMockState as () => any;
const _mockFetchResponse = (globalThis as any).mockFetchResponse as (
  url: string,
  status: number,
  body: string
) => void;

const MOCK_ADDRESS = '0x742d35Cc6634C0532925a3b844Bc454e4438f44e';
const ETH_RPC = 'https://eth.llamarpc.com';

function freshInit(overrides?: {
  storeData?: Record<string, unknown>;
  fetchResponses?: Record<string, { status: number; body: string }>;
}): void {
  _setup({
    storeData: overrides?.storeData ?? {},
    fetchResponses: overrides?.fetchResponses ?? {},
  });
  (globalThis as any).init();
}

// ─── init() ─────────────────────────────────────────────────────────────

_describe('init()', () => {
  _it('should load walletAddresses and networks from store', () => {
    freshInit({
      storeData: {
        config: {
          walletAddresses: [MOCK_ADDRESS],
          networks: [{ chain_id: '1', name: 'Ethereum', rpc_url: ETH_RPC, chain_type: 'evm' }],
        },
      },
    });
    const s = (globalThis as any).getState();
    _assertNotNull(s, 'getState should be defined');
    _assertEqual(s.config.walletAddresses.length, 1);
    _assertEqual(s.config.walletAddresses[0], MOCK_ADDRESS);
    _assertEqual(s.config.networks.length, 1);
    _assertEqual(s.config.networks[0].chain_id, '1');
  });

  _it('should have empty config when no store data', () => {
    freshInit();
    const s = (globalThis as any).getState();
    _assertEqual(s.config.walletAddresses.length, 0);
    _assertEqual(s.config.networks.length, 0);
  });
});

// ─── start() / stop() ──────────────────────────────────────────────────

_describe('start()', () => {
  _it('should set isRunning and publish state', () => {
    freshInit({ storeData: { config: { walletAddresses: [MOCK_ADDRESS], networks: [] } } });
    (globalThis as any).start();
    const mock = _getMockState();
    _assertEqual(mock.state['status'], 'running');
    _assertEqual(mock.state['walletCount'], 1);
  });
});

_describe('stop()', () => {
  _it('should set isRunning false and status stopped', () => {
    freshInit();
    (globalThis as any).start();
    (globalThis as any).stop();
    const s = (globalThis as any).getState();
    _assertEqual(s.isRunning, false);
    const mock = _getMockState();
    _assertEqual(mock.state['status'], 'stopped');
  });
});

// ─── onLoad() ───────────────────────────────────────────────────────────

_describe('onLoad()', () => {
  _it('should store walletAddress from params', () => {
    freshInit();
    (globalThis as any).onLoad({ walletAddress: MOCK_ADDRESS });
    const s = (globalThis as any).getState();
    _assertEqual(s.config.walletAddresses.length, 1);
    _assertEqual(s.config.walletAddresses[0], MOCK_ADDRESS);
  });

  _it('should store walletAddresses array from params', () => {
    freshInit();
    (globalThis as any).onLoad({
      walletAddresses: [MOCK_ADDRESS, '0x0000000000000000000000000000000000000001'],
    });
    const s = (globalThis as any).getState();
    _assertEqual(s.config.walletAddresses.length, 2);
  });

  _it('should not duplicate address if already present', () => {
    freshInit({ storeData: { config: { walletAddresses: [MOCK_ADDRESS], networks: [] } } });
    (globalThis as any).onLoad({ walletAddress: MOCK_ADDRESS });
    const s = (globalThis as any).getState();
    _assertEqual(s.config.walletAddresses.length, 1);
  });
});

// ─── Setup flow ────────────────────────────────────────────────────────

_describe('Setup flow', () => {
  _it('onSetupStart should return networks step with EVM options', () => {
    freshInit();
    const result = (globalThis as any).onSetupStart();
    _assertEqual(result.step.id, 'networks');
    _assertEqual(result.step.fields.length, 1);
    const evmField = result.step.fields.find((f: any) => f.name === 'evm_networks');
    _assertNotNull(evmField, 'should have evm_networks field');
    _assertTrue(Array.isArray(evmField.options) && evmField.options.length > 0);
  });

  _it('onSetupSubmit networks should save selected networks and return complete', () => {
    freshInit();
    (globalThis as any).onSetupStart();
    const result = (globalThis as any).onSetupSubmit({
      stepId: 'networks',
      values: { evm_networks: ['1', '137'] },
    });
    _assertEqual(result.status, 'complete');
    const s = (globalThis as any).getState();
    _assertEqual(s.config.networks.length, 2);
    const chainIds = s.config.networks.map((n: any) => n.chain_id).sort();
    _assertEqual(chainIds[0], '1');
    _assertEqual(chainIds[1], '137');
  });

  _it('onSetupSubmit networks with no selection should default to first 3 EVM', () => {
    freshInit();
    (globalThis as any).onSetupStart();
    (globalThis as any).onSetupSubmit({ stepId: 'networks', values: { evm_networks: [] } });
    const s = (globalThis as any).getState();
    _assertTrue(s.config.networks.length >= 1, 'should have at least one default network');
  });

  _it('onSetupSubmit unknown step should return error', () => {
    freshInit();
    const result = (globalThis as any).onSetupSubmit({ stepId: 'unknown_step', values: {} });
    _assertEqual(result.status, 'error');
    _assertTrue(Array.isArray(result.errors) && result.errors.length > 0);
  });

  _it('onSetupCancel should not throw', () => {
    freshInit();
    (globalThis as any).onSetupCancel();
  });
});

// ─── Tools ──────────────────────────────────────────────────────────────

_describe('Tools', () => {
  _it('list_wallets should return wallets from state', () => {
    freshInit({ storeData: { config: { walletAddresses: [MOCK_ADDRESS], networks: [] } } });
    const result = _callTool('list_wallets');
    _assertNotNull(result.wallets);
    _assertEqual(result.wallets.length, 1);
    _assertEqual(result.wallets[0].address, MOCK_ADDRESS);
    _assertEqual(result.wallets[0].chain_type, 'evm');
  });

  _it('list_wallets should return empty when no addresses', () => {
    freshInit();
    const result = _callTool('list_wallets');
    _assertEqual(result.wallets.length, 0);
  });

  _it('list_networks should return networks from state', () => {
    freshInit({
      storeData: {
        config: {
          walletAddresses: [],
          networks: [{ chain_id: '1', name: 'Ethereum', rpc_url: ETH_RPC, chain_type: 'evm' }],
        },
      },
    });
    const result = _callTool('list_networks');
    _assertNotNull(result.networks);
    _assertEqual(result.networks.length, 1);
    _assertEqual(result.networks[0].chain_id, '1');
    _assertEqual(result.networks[0].name, 'Ethereum');
  });

  _it('list_networks should return empty when no networks', () => {
    freshInit();
    const result = _callTool('list_networks');
    _assertEqual(result.networks.length, 0);
  });

  _it('get_balance should require address and chain_id', () => {
    freshInit({
      storeData: {
        config: {
          walletAddresses: [MOCK_ADDRESS],
          networks: [{ chain_id: '1', name: 'Ethereum', rpc_url: ETH_RPC, chain_type: 'evm' }],
        },
      },
    });
    const missingAddr = _callTool('get_balance', { chain_id: '1' });
    _assertNotNull(missingAddr.error);
    const missingChain = _callTool('get_balance', { address: MOCK_ADDRESS });
    _assertNotNull(missingChain.error);
  });

  _it('get_balance should return error when network not configured', () => {
    freshInit({ storeData: { config: { walletAddresses: [MOCK_ADDRESS], networks: [] } } });
    const result = _callTool('get_balance', { address: MOCK_ADDRESS, chain_id: '1' });
    _assertNotNull(result.error);
  });

  _it('get_balance should return balance when RPC responds', () => {
    const rpcBody = JSON.stringify({ jsonrpc: '2.0', id: 1, result: '0x0de0b6b3a7640000' });
    freshInit({
      storeData: {
        config: {
          walletAddresses: [MOCK_ADDRESS],
          networks: [{ chain_id: '1', name: 'Ethereum', rpc_url: ETH_RPC, chain_type: 'evm' }],
        },
      },
      fetchResponses: { [ETH_RPC]: { status: 200, body: rpcBody } },
    });
    const result = _callTool('get_balance', { address: MOCK_ADDRESS, chain_id: '1' });
    _assertNotNull(result, 'should return result');
    _assertEqual(result.address, MOCK_ADDRESS);
    _assertEqual(result.balance_wei, '0x0de0b6b3a7640000');
    _assertNotNull(result.balance_eth);
    _assertEqual(result.symbol, 'ETH');
  });

  _it('get_balance should return error when RPC fails', () => {
    freshInit({
      storeData: {
        config: {
          walletAddresses: [MOCK_ADDRESS],
          networks: [{ chain_id: '1', name: 'Ethereum', rpc_url: ETH_RPC, chain_type: 'evm' }],
        },
      },
      fetchResponses: { [ETH_RPC]: { status: 500, body: 'Internal Server Error' } },
    });
    const result = _callTool('get_balance', { address: MOCK_ADDRESS, chain_id: '1' });
    _assertNotNull(result.error);
  });
});
