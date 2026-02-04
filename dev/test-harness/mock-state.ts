/**
 * mock-state.ts - Shared mock state for V8 skill testing
 *
 * Maintains the state that would normally live in the Rust runtime's
 * bridge implementations.
 */

export interface MockState {
  /** store.get/set data */
  store: Record<string, unknown>;

  /** SQLite database mock */
  db: {
    tables: Record<string, DbTable>;
    kv: Record<string, unknown>;
  };

  /** Published state (state.set/setPartial) */
  state: Record<string, unknown>;

  /** Registered cron schedules */
  cronSchedules: Record<string, string>;

  /** platform.notify calls */
  notifications: Array<{ title: string; body?: string }>;

  /** URL -> mock response for net.fetch */
  fetchResponses: Record<string, { status: number; body: string; headers?: Record<string, string> }>;

  /** URL -> error message for net.fetch */
  fetchErrors: Record<string, string>;

  /** Recorded fetch calls */
  fetchCalls: Array<{ url: string; options?: FetchOptions }>;

  /** data.read/write files */
  dataFiles: Record<string, string>;

  /** Environment variables for platform.env */
  env: Record<string, string>;

  /** Return value for platform.os() */
  platformOs: string;

  /** skills.list() return value */
  peerSkills: SkillInfo[];

  /** Console output for debugging */
  consoleOutput: Array<{ level: string; message: string }>;

  /** Timer tracking */
  timers: Map<number, TimerEntry>;
  nextTimerId: number;
}

export interface DbTable {
  columns: string[];
  rows: Array<Record<string, unknown>>;
}

export interface FetchOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
  timeout?: number;
}

export interface SkillInfo {
  id: string;
  name: string;
  version?: string;
  status?: string;
}

export interface TimerEntry {
  callback: () => void;
  delay: number;
  isInterval: boolean;
  scheduledAt: number;
}

/** Global mock state instance */
let mockState: MockState = createFreshState();

function createFreshState(): MockState {
  return {
    store: {},
    db: {
      tables: {},
      kv: {},
    },
    state: {},
    cronSchedules: {},
    notifications: [],
    fetchResponses: {},
    fetchErrors: {},
    fetchCalls: [],
    dataFiles: {},
    env: {},
    platformOs: 'macos',
    peerSkills: [],
    consoleOutput: [],
    timers: new Map(),
    nextTimerId: 1,
  };
}

/** Get the current mock state */
export function getMockState(): MockState {
  return mockState;
}

/** Reset all mock state to initial values */
export function resetMockState(): void {
  mockState = createFreshState();
}

/** Initialize mock state with optional overrides */
export function initMockState(options?: {
  storeData?: Record<string, unknown>;
  fetchResponses?: Record<string, { status: number; body: string; headers?: Record<string, string> }>;
  fetchErrors?: Record<string, string>;
  env?: Record<string, string>;
  platformOs?: string;
  peerSkills?: SkillInfo[];
  dataFiles?: Record<string, string>;
}): void {
  resetMockState();

  if (options?.storeData) {
    mockState.store = { ...options.storeData };
  }
  if (options?.fetchResponses) {
    mockState.fetchResponses = { ...options.fetchResponses };
  }
  if (options?.fetchErrors) {
    mockState.fetchErrors = { ...options.fetchErrors };
  }
  if (options?.env) {
    mockState.env = { ...options.env };
  }
  if (options?.platformOs) {
    mockState.platformOs = options.platformOs;
  }
  if (options?.peerSkills) {
    mockState.peerSkills = [...options.peerSkills];
  }
  if (options?.dataFiles) {
    mockState.dataFiles = { ...options.dataFiles };
  }
}

/** Set up a mock fetch response for a URL */
export function mockFetchResponse(
  url: string,
  status: number,
  body: string,
  headers?: Record<string, string>
): void {
  mockState.fetchResponses[url] = { status, body, headers };
  delete mockState.fetchErrors[url];
}

/** Set up a mock fetch error for a URL */
export function mockFetchError(url: string, message = 'Network error'): void {
  mockState.fetchErrors[url] = message;
  delete mockState.fetchResponses[url];
}

/** Add environment variable */
export function setEnv(key: string, value: string): void {
  mockState.env[key] = value;
}

/** Set platform OS */
export function setPlatformOs(os: string): void {
  mockState.platformOs = os;
}
