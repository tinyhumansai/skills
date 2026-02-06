// Shared skill state module for Gmail skill
// Tools and lifecycle functions access state through globalThis.getGmailSkillState()
// This pattern works in both production V8 runtime and test harness sandbox.
import type { GmailProfile, SkillConfig, SyncStatus } from './types';

export interface GmailSkillState {
  config: SkillConfig;
  profile: GmailProfile | null;
  syncStatus: SyncStatus;
  activeSessions: string[];
  rateLimitRemaining: number;
  rateLimitReset: number;
  lastApiError: string | null;
}

// Extend globalThis type
declare global {
  function getGmailSkillState(): GmailSkillState;

  var __gmailSkillState: GmailSkillState;
}

/**
 * Initialize the Gmail skill state. Called once at module load.
 */
function initGmailSkillState(): GmailSkillState {
  const state: GmailSkillState = {
    config: {
      credentialId: '',
      userEmail: '',
      syncEnabled: true,
      syncIntervalMinutes: 15,
      maxEmailsPerSync: 100,
      notifyOnNewEmails: true,
    },
    profile: null,
    syncStatus: {
      lastSyncTime: 0,
      lastHistoryId: '',
      totalEmails: 0,
      newEmailsCount: 0,
      syncInProgress: false,
      nextSyncTime: 0,
    },
    activeSessions: [],
    rateLimitRemaining: 250,
    rateLimitReset: Date.now() + 3600000,
    lastApiError: null,
  };

  globalThis.__gmailSkillState = state;
  return state;
}

// Initialize on module load
initGmailSkillState();

// Expose getGmailSkillState as a global function
globalThis.getGmailSkillState = function getGmailSkillState(): GmailSkillState {
  const state = globalThis.__gmailSkillState;
  if (!state) {
    throw new Error('[gmail] Skill state not initialized');
  }
  return state;
};

// Re-export for TypeScript imports (won't be used at runtime, but satisfies compiler)
export function getGmailSkillState(): GmailSkillState {
  return globalThis.getGmailSkillState();
}
