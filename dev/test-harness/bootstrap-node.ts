/**
 * bootstrap-node.ts - Provides the same globals as Rust's bootstrap.js (Node.js version)
 *
 * Creates all the bridge APIs (db, net, platform, state, data, cron, skills)
 * with mock implementations backed by mock-state.ts.
 */

import { join } from 'path';
import { dbAll, dbExec, dbGet, dbKvGet, dbKvSet } from './mock-db';
import { getMockState, type FetchOptions, type HookEventMock, type HookFilterMock, type HookRegistrationMock } from './mock-state';
import { createPersistentData } from './persistent-data';
import { createPersistentDb, type PersistentDb } from './persistent-db';
import { createPersistentState } from './persistent-state';

export interface BridgeOptions {
  /** When set, db/state/data use file-backed storage in this directory */
  dataDir?: string;
}

/**
 * Create all bridge API globals and inject them into the provided context.
 * When options.dataDir is set, db/state/data use persistent file-backed storage.
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

  // State API - unified persistent key-value state
  let stateApi;
  if (dataDir) {
    const pState = createPersistentState(join(dataDir, 'state.json'));
    stateApi = {
      get: (key: string): unknown => pState.get(key),
      set: (key: string, value: unknown): void => { pState.set(key, value); },
      setPartial: (partial: Record<string, unknown>): void => { pState.setPartial(partial); },
      delete: (key: string): void => pState.delete(key),
      keys: (): string[] => pState.keys(),
    };
  } else {
    stateApi = {
      get: (key: string): unknown => state.state[key] ?? null,
      set: (key: string, value: unknown): void => { state.state[key] = value; },
      setPartial: (partial: Record<string, unknown>): void => {
        Object.assign(state.state, partial);
      },
      delete: (key: string): void => { delete state.state[key]; },
      keys: (): string[] => Object.keys(state.state),
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

  // OAuth API - credential management and authenticated proxy
  const oauth = {
    getCredential: (): unknown => {
      return state.oauthCredential;
    },
    fetch: (path: string, options?: Record<string, unknown>): { status: number; headers: Record<string, string>; body: string } => {
      state.oauthFetchCalls.push({ path, options });

      // Return 401 if no credential
      if (!state.oauthCredential) {
        return {
          status: 401,
          headers: {},
          body: JSON.stringify({ error: 'No OAuth credential. Complete setup first.' }),
        };
      }

      // Check for mock error
      if (state.oauthFetchErrors[path]) {
        throw new Error(state.oauthFetchErrors[path]);
      }

      // Check for mock response
      const mockResponse = state.oauthFetchResponses[path];
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
        body: JSON.stringify({ error: 'Not found (no OAuth mock configured)' }),
      };
    },
    revoke: (): boolean => {
      state.oauthCredential = null;
      state.oauthRevoked = true;
      return true;
    },
  };

  // Hooks API - event-based pub/sub system
  const hooks = {
    register: (definition: Record<string, unknown>): boolean => {
      const id = definition.id as string;
      if (!id) return false;
      state.hooks[id] = {
        id,
        description: (definition.description as string) ?? undefined,
        filter: (definition.filter as Record<string, unknown>) ?? {},
        accumulate: definition.accumulate as HookRegistrationMock['accumulate'],
        enabled: definition.enabled !== false,
        maxFires: definition.max_fires as number | undefined,
        priority: (definition.priority as number) ?? 0,
        fireCount: 0,
        lastFiredAt: null,
        buffer: {},
      };
      return true;
    },
    unregister: (hookId: string): boolean => {
      if (!state.hooks[hookId]) return false;
      delete state.hooks[hookId];
      return true;
    },
    update: (hookId: string, changes: Record<string, unknown>): boolean => {
      const hook = state.hooks[hookId];
      if (!hook) return false;
      if (changes.filter !== undefined) hook.filter = changes.filter as HookRegistrationMock['filter'];
      if (changes.description !== undefined) hook.description = changes.description as string;
      if (changes.accumulate !== undefined) hook.accumulate = changes.accumulate as HookRegistrationMock['accumulate'];
      if (changes.enabled !== undefined) hook.enabled = changes.enabled as boolean;
      if (changes.max_fires !== undefined) hook.maxFires = changes.max_fires as number;
      if (changes.priority !== undefined) hook.priority = changes.priority as number;
      return true;
    },
    setEnabled: (hookId: string, enabled: boolean): boolean => {
      const hook = state.hooks[hookId];
      if (!hook) return false;
      hook.enabled = enabled;
      return true;
    },
    list: (): unknown[] => {
      return Object.values(state.hooks).map((h) => ({
        id: h.id,
        enabled: h.enabled,
        filter: h.filter,
        fireCount: h.fireCount,
        lastFiredAt: h.lastFiredAt,
        maxFires: h.maxFires,
        priority: h.priority,
        hasAccumulation: !!h.accumulate,
      }));
    },
    emit: (event: Record<string, unknown>): number => {
      const hookEvent = event as unknown as HookEventMock;
      state.hookEvents.push(hookEvent);

      let matchCount = 0;
      const sortedHooks = Object.values(state.hooks)
        .filter((h) => h.enabled)
        .sort((a, b) => b.priority - a.priority);

      for (const hook of sortedHooks) {
        if (hook.maxFires !== undefined && hook.fireCount >= hook.maxFires) continue;
        if (!matchesFilter(hook.filter, hookEvent)) continue;

        matchCount++;

        if (hook.accumulate) {
          // Accumulate events
          const groupKey = hook.accumulate.group_by
            ? resolvePathValue(hookEvent, hook.accumulate.group_by)
            : '__default';
          const key = String(groupKey ?? '__default');
          if (!hook.buffer[key]) hook.buffer[key] = [];
          hook.buffer[key].push(hookEvent);

          // Check if accumulation threshold is met
          const count = hook.buffer[key].length;
          const threshold = hook.accumulate.count ?? 1;
          const minCount = hook.accumulate.min_count ?? 1;

          if (count >= threshold && count >= minCount) {
            fireHook(hook, hook.buffer[key], key !== '__default' ? key : undefined);
            if (hook.accumulate.reset_on_fire !== false) {
              hook.buffer[key] = [];
            }
          }
        } else {
          // Fire immediately
          fireHook(hook, [hookEvent], undefined);
        }
      }

      return matchCount;
    },
    getAccumulationState: (hookId: string): unknown => {
      const hook = state.hooks[hookId];
      if (!hook) return null;
      const groups: Record<string, number> = {};
      const allTimestamps: number[] = [];
      for (const [key, events] of Object.entries(hook.buffer)) {
        groups[key] = events.length;
        for (const e of events) allTimestamps.push(e.timestamp);
      }
      return {
        bufferedCount: allTimestamps.length,
        eventTimestamps: allTimestamps.sort((a, b) => a - b),
        groups,
      };
    },
  };

  /** Fire a hook: call onHookTriggered on the skill context */
  function fireHook(hook: HookRegistrationMock, events: HookEventMock[], groupKey?: string): void {
    hook.fireCount++;
    hook.lastFiredAt = Date.now();
    state.hookTriggers.push({ hookId: hook.id, events: [...events], groupKey });

    // The runtime would call onHookTriggered on the listener skill.
    // In the test harness, we check if the global onHookTriggered is defined.
    const onHookTriggered = (globalThis as Record<string, unknown>).onHookTriggered as
      | ((args: Record<string, unknown>) => unknown)
      | undefined;
    if (typeof onHookTriggered === 'function') {
      onHookTriggered({
        hookId: hook.id,
        event: events[events.length - 1],
        events,
        eventCount: events.length,
        groupKey,
        firstEventAt: events[0]?.timestamp ?? Date.now(),
        triggeredAt: Date.now(),
      });
    }
  }

  /** Resolve a dot-path value from a hook event (e.g. "entities.chat.id"). */
  function resolvePathValue(obj: unknown, path: string): unknown {
    const parts = path.split('.');
    let current: unknown = obj;
    for (const part of parts) {
      if (current == null || typeof current !== 'object') return undefined;
      current = (current as Record<string, unknown>)[part];
    }
    return current;
  }

  /** Check if a hook event matches a filter. */
  function matchesFilter(filter: HookFilterMock, event: HookEventMock): boolean {
    // event_types check (with glob support)
    if (filter.event_types && filter.event_types.length > 0) {
      const matched = filter.event_types.some((pattern) => {
        if (pattern.includes('*')) {
          const regex = new RegExp('^' + pattern.replace(/\./g, '\\.').replace(/\*/g, '.*') + '$');
          return regex.test(event.type);
        }
        return pattern === event.type;
      });
      if (!matched) return false;
    }

    // source_skills check
    if (filter.source_skills && filter.source_skills.length > 0) {
      if (!filter.source_skills.includes(event.source)) return false;
    }

    // entities check
    if (filter.entities) {
      for (const [role, entityFilter] of Object.entries(filter.entities)) {
        const entity = event.entities[role];
        if (!entity) return false;
        if (entityFilter.types && entityFilter.types.length > 0 && !entityFilter.types.includes(entity.type)) return false;
        if (entityFilter.ids && entityFilter.ids.length > 0 && !entityFilter.ids.includes(entity.id)) return false;
        if (entityFilter.properties) {
          for (const match of entityFilter.properties) {
            if (!evaluateMatch(entity.properties ?? {}, match.path, match.op, match.value)) return false;
          }
        }
      }
    }

    // data_match check
    if (filter.data_match) {
      for (const match of filter.data_match) {
        if (!evaluateMatch(event.data, match.path, match.op, match.value)) return false;
      }
    }

    // any_of: at least one sub-filter must match
    if (filter.any_of && filter.any_of.length > 0) {
      if (!filter.any_of.some((sub) => matchesFilter(sub, event))) return false;
    }

    // all_of: all sub-filters must match
    if (filter.all_of && filter.all_of.length > 0) {
      if (!filter.all_of.every((sub) => matchesFilter(sub, event))) return false;
    }

    // none_of: no sub-filter may match
    if (filter.none_of && filter.none_of.length > 0) {
      if (filter.none_of.some((sub) => matchesFilter(sub, event))) return false;
    }

    return true;
  }

  /** Evaluate a single data match condition. */
  function evaluateMatch(data: Record<string, unknown>, path: string, op: string, value?: unknown): boolean {
    const actual = resolvePathValue(data, path);
    switch (op) {
      case 'eq': return actual === value;
      case 'neq': return actual !== value;
      case 'gt': return typeof actual === 'number' && typeof value === 'number' && actual > value;
      case 'gte': return typeof actual === 'number' && typeof value === 'number' && actual >= value;
      case 'lt': return typeof actual === 'number' && typeof value === 'number' && actual < value;
      case 'lte': return typeof actual === 'number' && typeof value === 'number' && actual <= value;
      case 'contains': return typeof actual === 'string' && typeof value === 'string' && actual.includes(value);
      case 'not_contains': return typeof actual === 'string' && typeof value === 'string' && !actual.includes(value);
      case 'starts_with': return typeof actual === 'string' && typeof value === 'string' && actual.startsWith(value);
      case 'ends_with': return typeof actual === 'string' && typeof value === 'string' && actual.endsWith(value);
      case 'regex': return typeof actual === 'string' && typeof value === 'string' && new RegExp(value).test(actual);
      case 'in': return Array.isArray(value) && value.includes(actual);
      case 'not_in': return Array.isArray(value) && !value.includes(actual);
      case 'exists': return actual !== undefined && actual !== null;
      case 'not_exists': return actual === undefined || actual === null;
      default: return false;
    }
  }

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

  // Model API mock (generate / summarize routed to backend in production)
  const model = {
    generate: (prompt: string, _options?: { maxTokens?: number; temperature?: number }): string => {
      state.modelCalls.push({ type: 'generate', prompt });
      const mockResponse = state.modelResponses.shift();
      return mockResponse ?? `[mock generate response for: ${prompt}]`;
    },
    summarize: (text: string, _options?: { maxTokens?: number }): string => {
      state.modelCalls.push({ type: 'summarize', text });
      const mockResponse = state.modelResponses.shift();
      return mockResponse ?? `[mock summary of: ${text.slice(0, 50)}...]`;
    },
  };

  // Mock Buffer class
  const { Buffer: NodeBuffer } = await import('buffer');

  return {
    console,
    db,
    net,
    platform,
    state: stateApi,
    data,
    cron,
    skills,
    oauth,
    hooks,
    model,
    // Backend API - authenticated API client mock
    backend: {
      url: state.env['BACKEND_URL'] ?? 'https://api.alphahuman.xyz',
      token: state.env['JWT_TOKEN'] ?? '',
      fetch: (
        path: string,
        fetchOpts?: FetchOptions,
      ): { status: number; headers: Record<string, string>; body: string } => {
        state.backendFetchCalls.push({ path, options: fetchOpts });

        if (state.backendFetchErrors[path]) {
          throw new Error(state.backendFetchErrors[path]);
        }

        const mockResponse = state.backendFetchResponses[path];
        if (mockResponse) {
          return {
            status: mockResponse.status,
            headers: mockResponse.headers ?? {},
            body: mockResponse.body,
          };
        }

        return {
          status: 404,
          headers: {},
          body: JSON.stringify({ error: 'Not found (no backend mock configured)' }),
        };
      },
    },
    // Socket API - real-time events mock
    socket: {
      connected: (): boolean => false,
      id: (): string | undefined => undefined,
      emit: (event: string, ...args: unknown[]): void => {
        state.socketEmits.push({ event, args });
      },
      on: (event: string, _callback: (...args: unknown[]) => void): void => {
        state.socketListeners[event] = (state.socketListeners[event] ?? 0) + 1;
      },
      off: (event: string, _callback?: (...args: unknown[]) => void): void => {
        if (state.socketListeners[event]) {
          state.socketListeners[event]--;
          if (state.socketListeners[event] <= 0) delete state.socketListeners[event];
        }
      },
      disconnect: (): void => { /* no-op in test */ },
    },
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
    onOAuthComplete: undefined,
    onOAuthRevoked: undefined,
    onHookTriggered: undefined,
    // Cleanup hook for persistent DB
    __cleanup: () => {
      if (persistentDb) {
        persistentDb.close();
        persistentDb = null;
      }
    },
  };
}
