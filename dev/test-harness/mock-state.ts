/**
 * mock-state.ts - Shared mock state for QuickJS skill testing
 *
 * Maintains the state that would normally live in the Rust runtime's
 * bridge implementations.
 */

export interface MockState {
  /** SQLite database mock */
  db: {
    tables: Record<string, DbTable>;
    kv: Record<string, unknown>;
  };

  /** Persistent key-value state (state.get/set/setPartial/delete/keys) */
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

  /** OAuth mock credential */
  oauthCredential: OAuthCredentialMock | null;

  /** Recorded oauth.fetch calls */
  oauthFetchCalls: Array<{ path: string; options?: OAuthFetchOptionsMock }>;

  /** Path -> mock response for oauth.fetch */
  oauthFetchResponses: Record<string, { status: number; body: string; headers?: Record<string, string> }>;

  /** Path -> error message for oauth.fetch */
  oauthFetchErrors: Record<string, string>;

  /** Whether oauth.revoke() was called */
  oauthRevoked: boolean;

  /** Recorded model.generate/summarize calls */
  modelCalls: Array<{ type: string; prompt?: string; text?: string }>;

  /** Queue of mock responses for model.generate/summarize (shifted on each call) */
  modelResponses: string[];

  /** Registered hooks */
  hooks: Record<string, HookRegistrationMock>;

  /** Emitted hook events log */
  hookEvents: HookEventMock[];

  /** Hook trigger log (onHookTriggered calls) */
  hookTriggers: Array<{ hookId: string; events: HookEventMock[]; groupKey?: string }>;

  /** Recorded backend.fetch calls */
  backendFetchCalls: Array<{ path: string; options?: FetchOptions }>;

  /** Path -> mock response for backend.fetch */
  backendFetchResponses: Record<string, { status: number; body: string; headers?: Record<string, string> }>;

  /** Path -> error message for backend.fetch */
  backendFetchErrors: Record<string, string>;

  /** Recorded socket.emit calls */
  socketEmits: Array<{ event: string; args: unknown[] }>;

  /** Registered socket.on listeners (event -> count) */
  socketListeners: Record<string, number>;
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

export interface OAuthCredentialMock {
  credentialId: string;
  provider: string;
  scopes: string[];
  isValid: boolean;
  createdAt: number;
  accountLabel?: string;
}

export interface OAuthFetchOptionsMock {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
  timeout?: number;
  baseUrl?: string;
}

export interface HookEventMock {
  type: string;
  source: string;
  timestamp: number;
  entities: Record<string, { type: string; id: string; properties?: Record<string, unknown> }>;
  data: Record<string, unknown>;
}

export interface HookFilterMock {
  event_types?: string[];
  source_skills?: string[];
  entities?: Record<string, { types?: string[]; ids?: string[]; properties?: Array<{ path: string; op: string; value?: unknown }> }>;
  data_match?: Array<{ path: string; op: string; value?: unknown }>;
  any_of?: HookFilterMock[];
  all_of?: HookFilterMock[];
  none_of?: HookFilterMock[];
}

export interface HookRegistrationMock {
  id: string;
  description?: string;
  filter: HookFilterMock;
  accumulate?: {
    count?: number;
    window_ms?: number;
    group_by?: string;
    min_count?: number;
    reset_on_fire?: boolean;
  };
  enabled: boolean;
  maxFires?: number;
  priority: number;
  fireCount: number;
  lastFiredAt: number | null;
  /** Accumulated events buffer (keyed by group_by value or '__default') */
  buffer: Record<string, HookEventMock[]>;
}

/** Global mock state instance */
let mockState: MockState = createFreshState();

function createFreshState(): MockState {
  return {
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
    oauthCredential: null,
    oauthFetchCalls: [],
    oauthFetchResponses: {},
    oauthFetchErrors: {},
    oauthRevoked: false,
    modelCalls: [],
    modelResponses: [],
    hooks: {},
    hookEvents: [],
    hookTriggers: [],
    backendFetchCalls: [],
    backendFetchResponses: {},
    backendFetchErrors: {},
    socketEmits: [],
    socketListeners: {},
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
  stateData?: Record<string, unknown>;
  fetchResponses?: Record<string, { status: number; body: string; headers?: Record<string, string> }>;
  fetchErrors?: Record<string, string>;
  env?: Record<string, string>;
  platformOs?: string;
  peerSkills?: SkillInfo[];
  dataFiles?: Record<string, string>;
  oauthCredential?: OAuthCredentialMock;
  oauthFetchResponses?: Record<string, { status: number; body: string; headers?: Record<string, string> }>;
  backendFetchResponses?: Record<string, { status: number; body: string; headers?: Record<string, string> }>;
}): void {
  resetMockState();

  if (options?.stateData) {
    mockState.state = { ...options.stateData };
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
  if (options?.oauthCredential) {
    mockState.oauthCredential = { ...options.oauthCredential };
  }
  if (options?.oauthFetchResponses) {
    mockState.oauthFetchResponses = { ...options.oauthFetchResponses };
  }
  if (options?.backendFetchResponses) {
    mockState.backendFetchResponses = { ...options.backendFetchResponses };
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

/** Set up a mock OAuth credential */
export function mockOAuthCredential(credential: OAuthCredentialMock): void {
  mockState.oauthCredential = { ...credential };
  mockState.oauthRevoked = false;
}

/** Set up a mock OAuth fetch response for a path */
export function mockOAuthFetchResponse(
  path: string,
  status: number,
  body: string,
  headers?: Record<string, string>
): void {
  mockState.oauthFetchResponses[path] = { status, body, headers };
  delete mockState.oauthFetchErrors[path];
}

/** Set up a mock OAuth fetch error for a path */
export function mockOAuthFetchError(path: string, message = 'OAuth proxy error'): void {
  mockState.oauthFetchErrors[path] = message;
  delete mockState.oauthFetchResponses[path];
}

/** Queue a mock response for the next model.generate() or model.summarize() call */
export function mockModelResponse(response: string): void {
  mockState.modelResponses.push(response);
}

/** Set up a mock backend.fetch response for a path */
export function mockBackendFetchResponse(
  path: string,
  status: number,
  body: string,
  headers?: Record<string, string>,
): void {
  mockState.backendFetchResponses[path] = { status, body, headers };
  delete mockState.backendFetchErrors[path];
}

/** Set up a mock backend.fetch error for a path */
export function mockBackendFetchError(path: string, message = 'Backend error'): void {
  mockState.backendFetchErrors[path] = message;
  delete mockState.backendFetchResponses[path];
}
