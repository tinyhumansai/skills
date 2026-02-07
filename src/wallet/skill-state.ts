/**
 * skill-state.ts — global state for the wallet skill.
 * Wallet addresses come from the frontend via onLoad(params).
 */
import type { WalletSkillConfig } from './types';

export interface WalletSkillState {
  config: WalletSkillConfig;
  isRunning: boolean;
}

const _g = globalThis as Record<string, unknown>;

const state: WalletSkillState = { config: { walletAddresses: [], networks: [] }, isRunning: false };
_g.__walletSkillState = state;

// Assign to globalThis so bundled code can call it (esbuild can break named exports in IIFE bundle)
_g.getState = function getState(): WalletSkillState {
  return _g.__walletSkillState as WalletSkillState;
};

export function getState(): WalletSkillState {
  return (_g.getState as () => WalletSkillState)();
}
