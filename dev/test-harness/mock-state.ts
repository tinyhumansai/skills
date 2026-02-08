/**
 * mock-state.ts - Shared mock state for QuickJS skill testing
 *
 * Maintains the state that would normally live in the Rust runtime's
 * bridge implementations.
 */

export interface MockState {
  /** Persistent KV backing data (state.get/set reads/writes here) */
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

  /** model.generate/summarize call log */
  modelCalls: Array<{ method: string; prompt: string; options?: unknown }>;

  /** Prompt-substring → response mapping for model mock */
  modelResponses: Record<string, string>;

  /** Whether the mock model is available */
  modelAvailable: boolean;

  /** model.submitSummary() recorded submissions */
  summarySubmissions: Array<SummarySubmissionRecord>;

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

export interface SummarySubmissionRecord {
  summary: string;
  keyPoints?: string[];
  category?: string;
  sentiment?: 'positive' | 'neutral' | 'negative' | 'mixed';
  dataSource?: string;
  timeRange?: { start: number; end: number };
  entities?: Array<{
    id: string;
    type: string;
    name?: string;
    role?: string;
    metadata?: Record<string, unknown>;
  }>;
  metadata?: Record<string, unknown>;
  /** Timestamp when the mock recorded the submission */
  submittedAt: number;
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
    modelCalls: [],
    modelResponses: {},
    modelAvailable: true,
    summarySubmissions: [],
    oauthCredential: null,
    oauthFetchCalls: [],
    oauthFetchResponses: {},
    oauthFetchErrors: {},
    oauthRevoked: false,
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
  modelResponses?: Record<string, string>;
  modelAvailable?: boolean;
  oauthCredential?: OAuthCredentialMock;
  oauthFetchResponses?: Record<string, { status: number; body: string; headers?: Record<string, string> }>;
}): void {
  resetMockState();

  if (options?.stateData) {
    mockState.store = { ...options.stateData };
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
  if (options?.modelResponses) {
    mockState.modelResponses = { ...options.modelResponses };
  }
  if (options?.modelAvailable !== undefined) {
    mockState.modelAvailable = options.modelAvailable;
  }
  if (options?.oauthCredential) {
    mockState.oauthCredential = { ...options.oauthCredential };
  }
  if (options?.oauthFetchResponses) {
    mockState.oauthFetchResponses = { ...options.oauthFetchResponses };
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

/** Set up a mock model response for prompts containing a substring */
export function mockModelResponse(promptSubstring: string, response: string): void {
  mockState.modelResponses[promptSubstring] = response;
}

/** Set whether the mock model is available */
export function setModelAvailable(available: boolean): void {
  mockState.modelAvailable = available;
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
