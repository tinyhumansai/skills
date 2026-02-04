// Shared skill state module
// Tools and lifecycle functions access state through globalThis.getSkillState()
// This pattern works in both production V8 runtime and test harness sandbox.

import type { SkillConfig } from './types';

/**
 * Skill state interface - defines the shape of our mutable state
 */
export interface ServerPingState {
  config: SkillConfig;
  pingCount: number;
  failCount: number;
  consecutiveFails: number;
  wasDown: boolean;
  activeSessions: string[];
  pingIntervalId: number | null;
}

// Extend globalThis type
declare global {
  function getSkillState(): ServerPingState;
  // eslint-disable-next-line no-var
  var __skillState: ServerPingState;
}

/**
 * Initialize the skill state. Called once at module load.
 */
function initSkillState(): ServerPingState {
  const state: ServerPingState = {
    config: {
      serverUrl: '',
      pingIntervalSec: 10,
      notifyOnDown: true,
      notifyOnRecover: true,
      verboseLogging: false,
    },
    pingCount: 0,
    failCount: 0,
    consecutiveFails: 0,
    wasDown: false,
    activeSessions: [],
    pingIntervalId: null,
  };

  globalThis.__skillState = state;
  return state;
}

// Initialize on module load
initSkillState();

// Expose getSkillState as a global function
globalThis.getSkillState = function getSkillState(): ServerPingState {
  const state = globalThis.__skillState;
  if (!state) {
    throw new Error('[server-ping] Skill state not initialized');
  }
  return state;
};

// Re-export for TypeScript imports (won't be used at runtime, but satisfies compiler)
export function getSkillState(): ServerPingState {
  return globalThis.getSkillState();
}
