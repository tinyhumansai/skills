// Shared skill state module for Notion skill
// Tools and lifecycle functions access state through globalThis.getNotionSkillState()
// This pattern works in both production V8 runtime and test harness sandbox.

export interface NotionSkillConfig {
  credentialId: string;
  workspaceName: string;
  syncIntervalMinutes: number;
  contentSyncEnabled: boolean;
  maxPagesPerContentSync: number;
}

export interface NotionSyncStatus {
  syncInProgress: boolean;
  lastSyncTime: number;
  nextSyncTime: number;
  totalPages: number;
  totalDatabases: number;
  totalUsers: number;
  pagesWithContent: number;
  lastSyncError: string | null;
  lastSyncDurationMs: number;
}

export interface NotionSkillState {
  config: NotionSkillConfig;
  syncStatus: NotionSyncStatus;
  activeSessions: string[];
}

// Extend globalThis type
declare global {
  function getNotionSkillState(): NotionSkillState;

  var __notionSkillState: NotionSkillState;
}

/**
 * Initialize the Notion skill state. Called once at module load.
 */
function initNotionSkillState(): NotionSkillState {
  const s: NotionSkillState = {
    config: {
      credentialId: '',
      workspaceName: '',
      syncIntervalMinutes: 20,
      contentSyncEnabled: true,
      maxPagesPerContentSync: 50,
    },
    syncStatus: {
      syncInProgress: false,
      lastSyncTime: 0,
      nextSyncTime: 0,
      totalPages: 0,
      totalDatabases: 0,
      totalUsers: 0,
      pagesWithContent: 0,
      lastSyncError: null,
      lastSyncDurationMs: 0,
    },
    activeSessions: [],
  };

  globalThis.__notionSkillState = s;
  return s;
}

// Initialize on module load
initNotionSkillState();

// Expose getNotionSkillState as a global function
globalThis.getNotionSkillState = function getNotionSkillState(): NotionSkillState {
  const s = globalThis.__notionSkillState;
  if (!s) {
    throw new Error('[notion] Skill state not initialized');
  }
  return s;
};

// Re-export for TypeScript imports (won't be used at runtime, but satisfies compiler)
export function getNotionSkillState(): NotionSkillState {
  return globalThis.getNotionSkillState();
}
