/**
 * bootstrap-node.ts - Provides the same globals as Rust's bootstrap.js (Node.js version)
 *
 * Creates all the bridge APIs (db, store, net, platform, state, data, cron, skills)
 * with mock implementations backed by mock-state.ts.
 */

import { join } from 'path';
import { dbAll, dbExec, dbGet, dbKvGet, dbKvSet } from './mock-db';
import { getMockState, type FetchOptions } from './mock-state';
import { createPersistentData } from './persistent-data';
import { createPersistentDb, type PersistentDb } from './persistent-db';
import { createPersistentState } from './persistent-state';
import { createPersistentStore } from './persistent-store';

export interface BridgeOptions {
  /** When set, db/store/state/data use file-backed storage in this directory */
  dataDir?: string;
}

/**
 * Create all bridge API globals and inject them into the provided context.
 * When options.dataDir is set, db/store/state/data use persistent file-backed storage.
 */
export async function createBridgeAPIs(options?: BridgeOptions): Promise<Record<string, unknown>> {
  const state = getMockState();
  const dataDir = options?.dataDir;
  let persistentDb: PersistentDb | null = null;

  // Console - logs to mock state for inspection
  const console = {
    log: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      state.consoleOutput.push({ level: 'log', message });
      globalThis.console.log('[skill]', ...args);
    },
    info: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      state.consoleOutput.push({ level: 'info', message });
      globalThis.console.info('[skill]', ...args);
    },
    warn: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      state.consoleOutput.push({ level: 'warn', message });
      globalThis.console.warn('[skill]', ...args);
    },
    error: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      state.consoleOutput.push({ level: 'error', message });
      globalThis.console.error('[skill]', ...args);
    },
    debug: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      state.consoleOutput.push({ level: 'debug', message });
      globalThis.console.debug('[skill]', ...args);
    },
  };

  // Store API - persistent key-value store
  let store;
  if (dataDir) {
    const pStore = createPersistentStore(join(dataDir, 'store.json'));
    store = {
      get: (key: string): unknown => pStore.get(key),
      set: (key: string, value: unknown): void => pStore.set(key, value),
      delete: (key: string): void => pStore.delete(key),
      keys: (): string[] => pStore.keys(),
    };
  } else {
    store = {
      get: (key: string): unknown => state.store[key] ?? null,
      set: (key: string, value: unknown): void => { state.store[key] = value; },
      delete: (key: string): void => { delete state.store[key]; },
      keys: (): string[] => Object.keys(state.store),
    };
  }

  // Database API - SQLite (real or mock)
  let db;
  if (dataDir) {
    persistentDb = createPersistentDb(join(dataDir, 'skill.db'));
    const pDb = persistentDb;
    db = {
      exec: (sql: string, params?: unknown[]): void => pDb.exec(sql, params ?? []),
      get: (sql: string, params?: unknown[]): Record<string, unknown> | null => pDb.get(sql, params ?? []),
      all: (sql: string, params?: unknown[]): Array<Record<string, unknown>> => pDb.all(sql, params ?? []),
      kvGet: (key: string): unknown => pDb.kvGet(key),
      kvSet: (key: string, value: unknown): void => pDb.kvSet(key, value),
    };
  } else {
    db = {
      exec: (sql: string, params?: unknown[]): void => dbExec(sql, params ?? []),
      get: (sql: string, params?: unknown[]): Record<string, unknown> | null => dbGet(sql, params ?? []),
      all: (sql: string, params?: unknown[]): Array<Record<string, unknown>> => dbAll(sql, params ?? []),
      kvGet: (key: string): unknown => dbKvGet(key),
      kvSet: (key: string, value: unknown): void => dbKvSet(key, value),
    };
  }

  // Network API - HTTP mock
  const net = {
    fetch: (url: string, options?: FetchOptions): { status: number; headers: Record<string, string>; body: string } => {
      // Record the fetch call
      state.fetchCalls.push({ url, options });

      // Check for mock error
      if (state.fetchErrors[url]) {
        throw new Error(state.fetchErrors[url]);
      }

      // Check for mock response
      const mockResponse = state.fetchResponses[url];
      if (mockResponse) {
        return {
          status: mockResponse.status,
          headers: mockResponse.headers ?? {},
          body: mockResponse.body,
        };
      }

      // Default: return 404
      return {
        status: 404,
        headers: {},
        body: JSON.stringify({ error: 'Not found (no mock configured)' }),
      };
    },
  };

  // Platform API
  const platform = {
    os: (): string => {
      return state.platformOs;
    },
    env: (key: string): string => {
      return state.env[key] ?? '';
    },
    notify: (title: string, body?: string): void => {
      state.notifications.push({ title, body });
      globalThis.console.log(`[notification] ${title}${body ? ': ' + body : ''}`);
    },
  };

  // State API - frontend state publishing
  let stateApi;
  if (dataDir) {
    const pState = createPersistentState(join(dataDir, 'state.json'));
    stateApi = {
      get: (key: string): unknown => pState.get(key),
      set: (key: string, value: unknown): void => pState.set(key, value),
      setPartial: (partial: Record<string, unknown>): void => pState.setPartial(partial),
    };
  } else {
    stateApi = {
      get: (key: string): unknown => state.state[key],
      set: (key: string, value: unknown): void => { state.state[key] = value; },
      setPartial: (partial: Record<string, unknown>): void => { Object.assign(state.state, partial); },
    };
  }

  // Data API - file I/O
  let data;
  if (dataDir) {
    const pData = createPersistentData(join(dataDir, 'files'));
    data = {
      read: (filename: string): string | null => pData.read(filename),
      write: (filename: string, content: string): void => pData.write(filename, content),
    };
  } else {
    data = {
      read: (filename: string): string | null => state.dataFiles[filename] ?? null,
      write: (filename: string, content: string): void => { state.dataFiles[filename] = content; },
    };
  }

  // Cron API
  const cron = {
    register: (scheduleId: string, cronExpr: string): void => {
      state.cronSchedules[scheduleId] = cronExpr;
    },
    unregister: (scheduleId: string): void => {
      delete state.cronSchedules[scheduleId];
    },
    list: (): string[] => {
      return Object.keys(state.cronSchedules);
    },
  };

  // Skills API - inter-skill communication
  const skills = {
    list: () => {
      return state.peerSkills;
    },
    callTool: (_skillId: string, _toolName: string, _args?: Record<string, unknown>): unknown => {
      return { error: 'Inter-skill calls not supported in test harness' };
    },
  };

  // Model API - local LLM inference mock
  const model = {
    isAvailable: (): boolean => {
      return state.modelAvailable;
    },
    getStatus: (): Record<string, unknown> => {
      return {
        available: state.modelAvailable,
        loaded: state.modelAvailable,
        loading: false,
        downloaded: state.modelAvailable,
      };
    },
    generate: (prompt: string, options?: unknown): string => {
      state.modelCalls.push({ method: 'generate', prompt, options });
      for (const [substring, response] of Object.entries(state.modelResponses)) {
        if (prompt.includes(substring)) return response;
      }
      if (!state.modelAvailable) throw new Error('Model not available');
      return '(mock model response)';
    },
    summarize: (text: string, options?: unknown): string => {
      state.modelCalls.push({ method: 'summarize', prompt: text, options });
      if (!state.modelAvailable) throw new Error('Model not available');
      return '(mock summary)';
    },
    submitSummary: (submission: Record<string, unknown>): void => {
      if (
        !submission ||
        typeof (submission as any).summary !== 'string' ||
        ((submission as any).summary as string).trim() === ''
      ) {
        throw new Error('model.submitSummary: summary field is required and must be a non-empty string');
      }
      const s = submission as any;
      if (s.sentiment && !['positive', 'neutral', 'negative', 'mixed'].includes(s.sentiment)) {
        throw new Error(`model.submitSummary: invalid sentiment "${s.sentiment}"`);
      }
      if (s.timeRange) {
        if (typeof s.timeRange.start !== 'number' || typeof s.timeRange.end !== 'number') {
          throw new Error('model.submitSummary: timeRange.start and timeRange.end must be numbers');
        }
      }
      state.summarySubmissions.push({
        summary: s.summary,
        keyPoints: s.keyPoints,
        category: s.category,
        sentiment: s.sentiment,
        dataSource: s.dataSource,
        timeRange: s.timeRange,
        entities: s.entities,
        metadata: s.metadata,
        submittedAt: Date.now(),
      });
      globalThis.console.log(
        `[model.submitSummary] "${s.summary.substring(0, 80)}${s.summary.length > 80 ? '...' : ''}"`
      );
    },
  };

  // Timer mocks
  const setTimeout = (callback: () => void, delay = 0): number => {
    const id = state.nextTimerId++;
    state.timers.set(id, {
      callback,
      delay,
      isInterval: false,
      scheduledAt: Date.now(),
    });
    return id;
  };

  const setInterval = (callback: () => void, delay = 0): number => {
    const id = state.nextTimerId++;
    state.timers.set(id, {
      callback,
      delay,
      isInterval: true,
      scheduledAt: Date.now(),
    });
    return id;
  };

  const clearTimeout = (id: number): void => {
    state.timers.delete(id);
  };

  const clearInterval = (id: number): void => {
    state.timers.delete(id);
  };

  // Mock window.location
  const mockLocation = {
    protocol: 'https:',
    host: 'localhost',
    hostname: 'localhost',
    port: '',
    pathname: '/',
    search: '',
    hash: '',
    href: 'https://localhost/',
    origin: 'https://localhost',
  };

  // Mock event listeners storage
  const mockEventListeners: Map<string, Set<EventListener>> = new Map();

  const addEventListener = (type: string, listener: EventListener): void => {
    if (!mockEventListeners.has(type)) {
      mockEventListeners.set(type, new Set());
    }
    mockEventListeners.get(type)!.add(listener);
  };

  const removeEventListener = (type: string, listener: EventListener): void => {
    const listeners = mockEventListeners.get(type);
    if (listeners) {
      listeners.delete(listener);
    }
  };

  const dispatchEvent = (event: { type: string }): boolean => {
    const listeners = mockEventListeners.get(event.type);
    if (listeners) {
      listeners.forEach((listener) => {
        try {
          listener(event as Event);
        } catch (e) {
          globalThis.console.error(`Event listener error for ${event.type}:`, e);
        }
      });
    }
    return true;
  };

  // Try to import ws package for WebSocket
  let RealWebSocket: unknown;
  try {
    const wsModule = await import('ws');
    RealWebSocket = wsModule.default || wsModule.WebSocket;
    globalThis.console.log('[bootstrap] Using ws npm package for WebSocket');
  } catch {
    RealWebSocket = globalThis.WebSocket;
    globalThis.console.log('[bootstrap] Using native WebSocket (ws package not available)');
  }

  // Mock crypto
  const { webcrypto } = await import('crypto');
  const mockCrypto = {
    getRandomValues: <T extends ArrayBufferView>(array: T): T => {
      return (webcrypto as unknown as Crypto).getRandomValues(array);
    },
    subtle: (webcrypto as unknown as Crypto).subtle,
    randomUUID: () => (webcrypto as unknown as Crypto).randomUUID(),
  };

  // Mock Buffer class
  const { Buffer: NodeBuffer } = await import('buffer');

  return {
    console,
    store,
    db,
    net,
    platform,
    state: stateApi,
    data,
    cron,
    skills,
    model,
    setTimeout,
    setInterval,
    clearTimeout,
    clearInterval,
    // JavaScript globals
    Date,
    JSON,
    Object,
    Array,
    String,
    Number,
    Boolean,
    Math,
    Error,
    TypeError,
    ReferenceError,
    Map,
    Set,
    WeakMap,
    WeakSet,
    Promise,
    RegExp,
    Symbol,
    BigInt,
    parseInt,
    parseFloat,
    isNaN,
    isFinite,
    encodeURIComponent,
    decodeURIComponent,
    encodeURI,
    decodeURI,
    Uint8Array,
    Int8Array,
    Uint16Array,
    Int16Array,
    Uint32Array,
    Int32Array,
    Float32Array,
    Float64Array,
    ArrayBuffer,
    DataView,
    TextEncoder,
    TextDecoder,
    // Base64
    btoa: (str: string): string => NodeBuffer.from(str, 'binary').toString('base64'),
    atob: (str: string): string => NodeBuffer.from(str, 'base64').toString('binary'),
    // Browser-like globals
    location: mockLocation,
    WebSocket: RealWebSocket,
    crypto: mockCrypto,
    Buffer: NodeBuffer,
    // Browser event API mocks
    addEventListener,
    removeEventListener,
    dispatchEvent,
    navigator: {
      onLine: true,
      userAgent: 'Node.js/mock (test harness)',
    },
    // Pre-declare skill globals
    tools: [],
    init: undefined,
    start: undefined,
    stop: undefined,
    onCronTrigger: undefined,
    onSessionStart: undefined,
    onSessionEnd: undefined,
    onSetupStart: undefined,
    onSetupSubmit: undefined,
    onSetupCancel: undefined,
    onDisconnect: undefined,
    onListOptions: undefined,
    onSetOption: undefined,
    // Cleanup hook for persistent DB
    __cleanup: () => {
      if (persistentDb) {
        persistentDb.close();
        persistentDb = null;
      }
    },
  };
}
