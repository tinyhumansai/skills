// Shared skill state module for Telegram skill
// Tools and lifecycle functions access state through globalThis.getSkillState()
// This pattern works in both production V8 runtime and test harness sandbox.
import type { TdLibClient } from './tdlib-client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SkillConfig {
  phoneNumber: string;
  isAuthenticated: boolean;
  dataDir: string; // TDLib data directory path
  pendingCode: boolean;
}

export interface FormattedUser {
  id: string;
  firstName?: string;
  lastName?: string;
  username?: string;
  phoneNumber?: string;
  isBot?: boolean;
  isPremium?: boolean;
}

export interface FormattedDialog {
  id: string;
  title: string;
  type: 'user' | 'chat' | 'channel';
  unreadCount: number;
  lastMessage: string | null;
  isPinned: boolean;
}

export interface Cache {
  me: FormattedUser | null;
  dialogs: FormattedDialog[];
  lastSync: number;
}

export interface SetupSubmitArgs {
  stepId: string;
  values: Record<string, unknown>;
}

/**
 * TDLib authorization state for tracking login flow.
 */
export type AuthorizationState =
  | 'waitTdlibParameters'
  | 'waitPhoneNumber'
  | 'waitCode'
  | 'waitPassword'
  | 'ready'
  | 'closed'
  | 'unknown';

/**
 * Sync state tracking.
 */
export interface SyncState {
  inProgress: boolean;
  completed: boolean;
  lastSyncTime: number | null;
  error: string | null;
}

/**
 * Storage statistics.
 */
export interface StorageState {
  chatCount: number;
  messageCount: number;
  contactCount: number;
  unreadCount: number;
}

/**
 * Telegram skill state interface - defines the shape of our mutable state
 */
export interface TelegramState {
  config: SkillConfig;
  cache: Cache;
  client: TdLibClient | null;
  clientConnecting: boolean;
  clientError: string | null;
  authState: AuthorizationState;
  passwordHint: string | null;
  workerRunning: boolean;
  workerTimeoutId: ReturnType<typeof setTimeout> | null;
  sync: SyncState;
  storage: StorageState;
}

// ---------------------------------------------------------------------------
// Global Type Extension
// ---------------------------------------------------------------------------

declare global {
  function getTelegramSkillState(): TelegramState;

  var __telegramSkillState: TelegramState;
}

// ---------------------------------------------------------------------------
// State Initialization
// ---------------------------------------------------------------------------

/**
 * Initialize the skill state. Called once at module load.
 */
function initSkillState(): TelegramState {
  const state: TelegramState = {
    config: { phoneNumber: '', isAuthenticated: false, dataDir: '', pendingCode: false },
    cache: { me: null, dialogs: [], lastSync: 0 },
    client: null,
    clientConnecting: false,
    clientError: null,
    authState: 'unknown',
    passwordHint: null,
    workerRunning: false,
    workerTimeoutId: null,
    sync: { inProgress: false, completed: false, lastSyncTime: null, error: null },
    storage: { chatCount: 0, messageCount: 0, contactCount: 0, unreadCount: 0 },
  };

  globalThis.__telegramSkillState = state;
  return state;
}

// Initialize on module load
initSkillState();

// Expose getSkillState as a global function
globalThis.getTelegramSkillState = function getTelegramSkillState(): TelegramState {
  const state = globalThis.__telegramSkillState;
  if (!state) {
    throw new Error('[telegram] Skill state not initialized');
  }
  return state;
};

// Re-export for TypeScript imports (won't be used at runtime, but satisfies compiler)
export function getTelegramSkillState(): TelegramState {
  return globalThis.getTelegramSkillState();
}
