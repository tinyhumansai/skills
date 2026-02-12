/**
 * bootstrap-live.ts - Live bridge APIs for development and interactive testing
 *
 * Unlike bootstrap-node.ts (which mocks everything for unit tests), this
 * bootstrap provides real HTTP via curl, persistent file-backed storage,
 * and real platform APIs from the host process.
 *
 * Used by runner-node.ts and repl-node.ts for development workflows.
 */

import { execFileSync } from 'child_process';
import { existsSync, readFileSync, unlinkSync } from 'fs';
import { tmpdir } from 'os';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

import { type Socket, io } from 'socket.io-client';

import { createPersistentData } from './persistent-data';
import { createPersistentDb, type PersistentDb } from './persistent-db';
import { createPersistentState } from './persistent-state';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '..', '..');

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LiveBridgeOptions {
  /** Directory for persistent file-backed storage (db, state, files) */
  dataDir: string;
  /** JWT token for authenticating with the backend API */
  jwtToken?: string;
  /** Backend API URL (default: https://api.alphahuman.xyz) */
  backendUrl?: string;
}

export interface FetchOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
  timeout?: number;
}

interface TimerEntry {
  callback: () => void;
  delay: number;
  isInterval: boolean;
  scheduledAt: number;
}

export interface LiveState {
  /** Captured console output */
  consoleOutput: Array<{ level: string; message: string }>;
  /** Recorded HTTP requests */
  fetchCalls: Array<{ url: string; options?: FetchOptions }>;
  /** platform.notify() calls */
  notifications: Array<{ title: string; body?: string }>;
  /** Registered cron schedules */
  cronSchedules: Record<string, string>;
  /** Timer tracking for manual triggering */
  timers: Map<number, TimerEntry>;
  nextTimerId: number;
}

// ---------------------------------------------------------------------------
// Live State (tracking for debugging/inspection)
// ---------------------------------------------------------------------------

let liveState: LiveState = createFreshState();

function createFreshState(): LiveState {
  return {
    consoleOutput: [],
    fetchCalls: [],
    notifications: [],
    cronSchedules: {},
    timers: new Map(),
    nextTimerId: 1,
  };
}

/** Get the live tracking state (console output, fetch calls, cron, timers) */
export function getLiveState(): LiveState {
  return liveState;
}

/** Reset tracking state */
export function resetLiveState(): void {
  liveState = createFreshState();
}

// ---------------------------------------------------------------------------
// Real synchronous HTTP fetch via curl
// ---------------------------------------------------------------------------

function realFetch(
  url: string,
  options?: FetchOptions,
): { status: number; headers: Record<string, string>; body: string } {
  liveState.fetchCalls.push({ url, options });

  const headerFile = join(
    tmpdir(),
    `.skill-fetch-${Date.now()}-${Math.random().toString(36).slice(2)}`,
  );

  try {
    const args: string[] = [
      '-s', // silent (no progress bar)
      '-S', // show errors
      '-L', // follow redirects
      '-D',
      headerFile, // dump response headers to file
      '-w',
      '\n__HTTP_STATUS__%{http_code}', // append status code to output
      '--max-time',
      String(Math.ceil((options?.timeout ?? 30000) / 1000)),
    ];

    if (options?.method) {
      args.push('-X', options.method);
    }

    if (options?.headers) {
      for (const [key, value] of Object.entries(options.headers)) {
        args.push('-H', `${key}: ${value}`);
      }
    }

    if (options?.body) {
      args.push('--data-raw', options.body);
    }

    args.push('--', url);

    const raw = execFileSync('curl', args, {
      encoding: 'utf-8',
      maxBuffer: 50 * 1024 * 1024,
      timeout: (options?.timeout ?? 30000) + 5000,
    });

    // Extract status code from the --write-out marker appended after body
    const statusMarker = '\n__HTTP_STATUS__';
    const statusIdx = raw.lastIndexOf(statusMarker);
    let status = 0;
    let body = raw;
    if (statusIdx !== -1) {
      status = parseInt(raw.substring(statusIdx + statusMarker.length).trim(), 10);
      body = raw.substring(0, statusIdx);
    }

    // Parse response headers from the dump file
    const headers: Record<string, string> = {};
    if (existsSync(headerFile)) {
      const rawHeaders = readFileSync(headerFile, 'utf-8');
      // With -L (follow redirects), multiple header blocks may exist. Take the last.
      const blocks = rawHeaders.split(/\r?\n\r?\n/).filter((b) => b.trim());
      const lastBlock = blocks[blocks.length - 1] || '';
      for (const line of lastBlock.split(/\r?\n/)) {
        const colonIdx = line.indexOf(':');
        if (colonIdx > 0) {
          headers[line.substring(0, colonIdx).trim().toLowerCase()] = line
            .substring(colonIdx + 1)
            .trim();
        }
      }
    }

    return { status, headers, body };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes('ENOENT') || msg.includes('not found')) {
      throw new Error(
        'curl not found. Install curl to use live HTTP fetch.\n' +
          '  macOS: curl is pre-installed\n' +
          '  Linux: apt install curl / dnf install curl\n' +
          '  Windows: install curl or use Git Bash',
      );
    }
    throw new Error(`net.fetch failed: ${msg}`);
  } finally {
    try {
      if (existsSync(headerFile)) unlinkSync(headerFile);
    } catch {
      /* ignore cleanup errors */
    }
  }
}

// ---------------------------------------------------------------------------
// Create Bridge APIs
// ---------------------------------------------------------------------------

/**
 * Create all bridge API globals backed by real implementations.
 * - net.fetch: real HTTP via curl (synchronous)
 * - db/state/data: persistent file-backed storage in dataDir
 * - platform.os/env: real values from the host process
 */
export async function createBridgeAPIs(
  options: LiveBridgeOptions,
): Promise<Record<string, unknown>> {
  const { dataDir } = options;
  const backendUrl = options.backendUrl ?? 'https://api.alphahuman.xyz';
  const jwtToken = options.jwtToken ?? '';
  let persistentDb: PersistentDb | null = null;

  // Console — captures output for inspection AND logs to real console
  const console = {
    log: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      liveState.consoleOutput.push({ level: 'log', message });
      globalThis.console.log('[skill]', ...args);
    },
    info: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      liveState.consoleOutput.push({ level: 'info', message });
      globalThis.console.info('[skill]', ...args);
    },
    warn: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      liveState.consoleOutput.push({ level: 'warn', message });
      globalThis.console.warn('[skill]', ...args);
    },
    error: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      liveState.consoleOutput.push({ level: 'error', message });
      globalThis.console.error('[skill]', ...args);
    },
    debug: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      liveState.consoleOutput.push({ level: 'debug', message });
      globalThis.console.debug('[skill]', ...args);
    },
  };

  // Database — persistent SQLite via better-sqlite3
  persistentDb = createPersistentDb(join(dataDir, 'skill.db'));
  const pDb = persistentDb;
  const db = {
    exec: (sql: string, params?: unknown[]): void => pDb.exec(sql, params ?? []),
    get: (sql: string, params?: unknown[]): Record<string, unknown> | null =>
      pDb.get(sql, params ?? []),
    all: (sql: string, params?: unknown[]): Array<Record<string, unknown>> =>
      pDb.all(sql, params ?? []),
    kvGet: (key: string): unknown => pDb.kvGet(key),
    kvSet: (key: string, value: unknown): void => pDb.kvSet(key, value),
  };

  // Network — real synchronous HTTP via curl
  const net = {
    fetch: (
      url: string,
      fetchOpts?: FetchOptions,
    ): { status: number; headers: Record<string, string>; body: string } => {
      globalThis.console.log(`[net.fetch] ${fetchOpts?.method ?? 'GET'} ${url}`);
      return realFetch(url, fetchOpts);
    },
  };

  // Platform — real host APIs
  const platform = {
    os: (): string => {
      const p = process.platform;
      if (p === 'darwin') return 'macos';
      if (p === 'win32') return 'windows';
      return p;
    },
    env: (key: string): string => {
      if (key === 'BACKEND_URL') return backendUrl;
      if (key === 'JWT_TOKEN') return jwtToken;
      return process.env[key] ?? '';
    },
    notify: (title: string, body?: string): void => {
      liveState.notifications.push({ title, body });
      globalThis.console.log(`[notification] ${title}${body ? ': ' + body : ''}`);
    },
  };

  // Backend — authenticated API client for the AlphaHuman backend
  const backend = {
    url: backendUrl,
    token: jwtToken,
    fetch: (
      path: string,
      fetchOpts?: FetchOptions,
    ): { status: number; headers: Record<string, string>; body: string } => {
      const fullUrl = `${backendUrl}${path.startsWith('/') ? path : '/' + path}`;
      const mergedHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(jwtToken ? { Authorization: `Bearer ${jwtToken}` } : {}),
        ...(fetchOpts?.headers ?? {}),
      };
      globalThis.console.log(`[backend.fetch] ${fetchOpts?.method ?? 'GET'} ${fullUrl}`);
      return realFetch(fullUrl, { ...fetchOpts, headers: mergedHeaders });
    },
  };

  // TDLib — real TDLib FFI bridge for Telegram skill testing
  let tdlibBridge: import('./tdlib-bridge').TdLibBridge | null = null;
  let tdlibAvailable = false;
  try {
    const { TdLibBridge } = await import('./tdlib-bridge');
    tdlibBridge = new TdLibBridge();
    tdlibAvailable = tdlibBridge.isAvailable();
    if (tdlibAvailable) {
      globalThis.console.log('[bootstrap-live] TDLib bridge available');
    }
  } catch {
    globalThis.console.log('[bootstrap-live] TDLib bridge not available (missing deps)');
  }

  const tdlib = tdlibAvailable && tdlibBridge
    ? {
        isAvailable: () => tdlibBridge !== null,
        ensureInitialized: (dataDir: string) => {
          if (!tdlibBridge) return Promise.reject(new Error('TDLib bridge destroyed'));
          return tdlibBridge.ensureInitialized(dataDir);
        },
        createClient: (dir: string) => {
          if (!tdlibBridge) return Promise.reject(new Error('TDLib bridge destroyed'));
          return tdlibBridge.createClient(dir);
        },
        send: (requestJson: string) => {
          if (!tdlibBridge) return Promise.reject(new Error('TDLib bridge destroyed'));
          return tdlibBridge.send(requestJson);
        },
        receive: (timeoutMs: number) => {
          if (!tdlibBridge) return Promise.resolve(null);
          return tdlibBridge.receive(timeoutMs);
        },
        destroy: () => {
          if (!tdlibBridge) return Promise.resolve();
          return tdlibBridge.destroy();
        },
      }
    : {
        isAvailable: () => false,
        ensureInitialized: () => Promise.reject(new Error('TDLib not available')),
        createClient: () => Promise.reject(new Error('TDLib not available')),
        send: () => Promise.reject(new Error('TDLib not available')),
        receive: () => Promise.resolve(null),
        destroy: () => Promise.resolve(),
      };

  // OAuth state — managed by the REPL/runner for dev mode
  let oauthCredential: {
    credentialId: string;
    provider: string;
    scopes: string[];
    isValid: boolean;
    createdAt: number;
    accountLabel?: string;
  } | null = null;

  // Socket.io — connect to backend for real-time events
  let socket: Socket | null = null;
  if (jwtToken) {
    socket = io(backendUrl, {
      auth: { token: jwtToken },
      transports: ['polling', 'websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    socket.on('connect', () => {
      globalThis.console.log(`[socket] Connected (id: ${socket!.id})`);
    });
    socket.on('disconnect', (reason) => {
      globalThis.console.log(`[socket] Disconnected: ${reason}`);
    });
    socket.on('connect_error', (err) => {
      globalThis.console.warn(`[socket] Connection error: ${err.message}`);
    });
  }

  const socketApi = {
    connected: (): boolean => socket?.connected ?? false,
    id: (): string | undefined => socket?.id,
    emit: (event: string, ...args: unknown[]): void => {
      if (!socket) {
        globalThis.console.warn('[socket] Not connected (no JWT token provided)');
        return;
      }
      socket.emit(event, ...args);
    },
    on: (event: string, callback: (...args: unknown[]) => void): void => {
      if (!socket) {
        globalThis.console.warn('[socket] Not connected (no JWT token provided)');
        return;
      }
      socket.on(event, callback);
    },
    off: (event: string, callback?: (...args: unknown[]) => void): void => {
      if (!socket) return;
      socket.off(event, callback);
    },
    disconnect: (): void => {
      socket?.disconnect();
    },
  };

  // State — unified persistent key-value state
  const stateFilePath = join(dataDir, 'state.json');
  const pState = createPersistentState(stateFilePath);
  const stateApi = {
    get: (key: string): unknown => pState.get(key),
    set: (key: string, value: unknown): void => { pState.set(key, value); },
    setPartial: (partial: Record<string, unknown>): void => { pState.setPartial(partial); },
    delete: (key: string): void => pState.delete(key),
    keys: (): string[] => pState.keys(),
    /** Read all state entries (for REPL/debugging only, not part of bridge contract) */
    __getAll: (): Record<string, unknown> => {
      try {
        return JSON.parse(readFileSync(stateFilePath, 'utf-8'));
      } catch {
        return {};
      }
    },
  };

  // Data — persistent file I/O in scoped directory
  const pData = createPersistentData(join(dataDir, 'files'));
  const data = {
    read: (filename: string): string | null => pData.read(filename),
    write: (filename: string, content: string): void => pData.write(filename, content),
  };

  // Cron — tracked in live state for manual triggering
  const cron = {
    register: (scheduleId: string, cronExpr: string): void => {
      liveState.cronSchedules[scheduleId] = cronExpr;
    },
    unregister: (scheduleId: string): void => {
      delete liveState.cronSchedules[scheduleId];
    },
    list: (): string[] => Object.keys(liveState.cronSchedules),
  };

  // Skills — stub (inter-skill calls not supported in dev harness)
  const skills = {
    list: () => [],
    callTool: (
      _skillId: string,
      _toolName: string,
      _args?: Record<string, unknown>,
    ): unknown => {
      return { error: 'Inter-skill calls not supported in dev harness' };
    },
  };

  // OAuth — credential management and authenticated API proxy
  // Backend endpoints used:
  //   GET  /auth/:provider/connect        → { oauthUrl, state }
  //   ALL  /proxy/by-id/:integrationId/*  → proxied API call
  //   DELETE /auth/integrations/:id        → revoke integration
  const oauth = {
    getCredential: (): unknown => oauthCredential,
    fetch: async (
      path: string,
      fetchOpts?: {
        method?: string;
        headers?: Record<string, string>;
        body?: string;
        timeout?: number;
        baseUrl?: string;
      },
    ): Promise<{ status: number; headers: Record<string, string>; body: string; }> => {
      if (!oauthCredential) {
        return {
          status: 401,
          headers: {},
          body: JSON.stringify({ error: 'No OAuth credential. Complete OAuth setup first.' }),
        };
      }
      // Proxy through backend: /proxy/by-id/:integrationId/:path
      // The backend looks up the stored OAuth token and forwards with Authorization header.
      const cleanPath = path.startsWith('/') ? path.slice(1) : path;
      const proxyUrl = `${backendUrl}/proxy/by-id/${oauthCredential.credentialId}/${cleanPath}`;
      const method = fetchOpts?.method || 'GET';
      globalThis.console.log(`[oauth.fetch] ${method} ${path}`);
      const res = await realFetch(proxyUrl, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(jwtToken ? { Authorization: `Bearer ${jwtToken}` } : {}),
          ...(fetchOpts?.headers ?? {}),
        },
        body: fetchOpts?.body,
        timeout: fetchOpts?.timeout ? fetchOpts.timeout * 1000 : 30000,
      });

      return {
        status: res.status,
        headers: res.headers,
        body: res.body,
      };
    },
    revoke: (): boolean => {
      if (oauthCredential && jwtToken) {
        try {
          // DELETE /auth/integrations/:integrationId
          realFetch(
            `${backendUrl}/auth/integrations/${oauthCredential.credentialId}`,
            {
              method: 'DELETE',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${jwtToken}`,
              },
            },
          );
        } catch {
          /* best effort */
        }
      }
      oauthCredential = null;
      return true;
    },
    /** Internal: set credential (used by REPL OAuth flow) */
    __setCredential: (
      cred: {
        credentialId: string;
        provider: string;
        scopes: string[];
        isValid: boolean;
        createdAt: number;
        accountLabel?: string;
      } | null,
    ): void => {
      oauthCredential = cred;
    },
  };

  // Timers — use real timers so async skill code (Promises, update loops) works.
  // Also tracked in live state for debugging/inspection.
  const realTimers = new Map<number, ReturnType<typeof globalThis.setTimeout>>();

  const setTimeout = (callback: () => void, delay = 0): number => {
    const id = liveState.nextTimerId++;
    liveState.timers.set(id, {
      callback,
      delay,
      isInterval: false,
      scheduledAt: Date.now(),
    });
    const handle = globalThis.setTimeout(() => {
      liveState.timers.delete(id);
      realTimers.delete(id);
      callback();
    }, delay);
    realTimers.set(id, handle);
    return id;
  };

  const setInterval = (callback: () => void, delay = 0): number => {
    const id = liveState.nextTimerId++;
    liveState.timers.set(id, {
      callback,
      delay,
      isInterval: true,
      scheduledAt: Date.now(),
    });
    const handle = globalThis.setInterval(() => {
      callback();
    }, delay);
    realTimers.set(id, handle);
    return id;
  };

  const clearTimeout = (id: number): void => {
    liveState.timers.delete(id);
    const handle = realTimers.get(id);
    if (handle !== undefined) {
      globalThis.clearTimeout(handle);
      realTimers.delete(id);
    }
  };

  const clearInterval = (id: number): void => {
    liveState.timers.delete(id);
    const handle = realTimers.get(id);
    if (handle !== undefined) {
      globalThis.clearInterval(handle);
      realTimers.delete(id);
    }
  };

  // Browser-like globals (required by some skills)
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

  const mockEventListeners: Map<string, Set<EventListener>> = new Map();

  const addEventListener = (type: string, listener: EventListener): void => {
    if (!mockEventListeners.has(type)) {
      mockEventListeners.set(type, new Set());
    }
    mockEventListeners.get(type)!.add(listener);
  };

  const removeEventListener = (type: string, listener: EventListener): void => {
    mockEventListeners.get(type)?.delete(listener);
  };

  const dispatchEvent = (event: { type: string }): boolean => {
    mockEventListeners.get(event.type)?.forEach((listener) => {
      try {
        listener(event as Event);
      } catch (e) {
        globalThis.console.error(`Event listener error for ${event.type}:`, e);
      }
    });
    return true;
  };

  // // WebSocket via ws npm package
  // let RealWebSocket: unknown;
  // try {
  //   const wsModule = await import('ws');
  //   RealWebSocket = wsModule.default || wsModule.WebSocket;
  //   globalThis.console.log('[bootstrap-live] Using ws npm package for WebSocket');
  // } catch {
  //   RealWebSocket = globalThis.WebSocket;
  //   globalThis.console.log(
  //     '[bootstrap-live] Using native WebSocket (ws package not available)',
  //   );
  // }

  // Crypto from node:crypto
  const { webcrypto } = await import('crypto');
  const liveCrypto = {
    getRandomValues: <T extends ArrayBufferView>(array: T): T => {
      return (webcrypto as unknown as Crypto).getRandomValues(array);
    },
    subtle: (webcrypto as unknown as Crypto).subtle,
    randomUUID: () => (webcrypto as unknown as Crypto).randomUUID(),
  };

  // Buffer from node:buffer
  const { Buffer: NodeBuffer } = await import('buffer');

  return {
    console,
    db,
    net,
    platform,
    backend,
    socket: socketApi,
    state: stateApi,
    data,
    cron,
    skills,
    oauth,
    tdlib,
    // Hooks API stub - in live mode, hooks are handled by the Rust runtime.
    // This stub allows skills using hooks to load without errors.
    hooks: {
      register: (): boolean => { globalThis.console.log('[hooks] register (live stub)'); return true; },
      unregister: (): boolean => { globalThis.console.log('[hooks] unregister (live stub)'); return true; },
      update: (): boolean => { globalThis.console.log('[hooks] update (live stub)'); return true; },
      setEnabled: (): boolean => { globalThis.console.log('[hooks] setEnabled (live stub)'); return true; },
      list: (): unknown[] => [],
      emit: (): number => 0,
      getAccumulationState: (): unknown => null,
    },
    // Model API - routes to backend in live mode
    model: {
      generate: (prompt: string, options?: { maxTokens?: number; temperature?: number }): string => {
        const body: Record<string, unknown> = { prompt };
        if (options?.maxTokens) body.maxTokens = options.maxTokens;
        if (options?.temperature) body.temperature = options.temperature;
        const resp = realFetch(`${backendUrl}/api/ai/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${jwtToken}` },
          body: JSON.stringify(body),
          timeout: 30000,
        });
        if (resp.status >= 400) throw new Error(`Backend returned ${resp.status}: ${resp.body}`);
        const data = JSON.parse(resp.body);
        return data.text || '';
      },
      summarize: (text: string, options?: { maxTokens?: number }): string => {
        const body: Record<string, unknown> = { text };
        if (options?.maxTokens) body.maxTokens = options.maxTokens;
        const resp = realFetch(`${backendUrl}/api/ai/summarize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${jwtToken}` },
          body: JSON.stringify(body),
          timeout: 30000,
        });
        if (resp.status >= 400) throw new Error(`Backend returned ${resp.status}: ${resp.body}`);
        const data = JSON.parse(resp.body);
        return data.summary || '';
      },
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
    AbortController,
    AbortSignal,
    // Base64
    btoa: (str: string): string => NodeBuffer.from(str, 'binary').toString('base64'),
    atob: (str: string): string => NodeBuffer.from(str, 'base64').toString('binary'),
    // Browser-like globals
    location: mockLocation,
    // WebSocket: RealWebSocket,
    crypto: liveCrypto,
    Buffer: NodeBuffer,
    // Browser event API
    addEventListener,
    removeEventListener,
    dispatchEvent,
    navigator: {
      onLine: true,
      userAgent: 'Node.js/live (dev harness)',
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
    // Cleanup hook for persistent DB, socket, and TDLib
    __cleanup: () => {
      if (tdlibBridge && tdlibAvailable) {
        tdlibBridge.destroy().catch(() => { /* best effort */ });
        tdlibBridge = null;
      }
      if (socket) {
        socket.disconnect();
        socket = null;
      }
      if (persistentDb) {
        persistentDb.close();
        persistentDb = null;
      }
    },
  };
}
