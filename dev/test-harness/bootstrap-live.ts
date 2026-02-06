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

import { ModelBridge, type ModelGenerateOptions, type ModelSummarizeOptions } from './model-bridge';
import { createPersistentData } from './persistent-data';
import { createPersistentDb, type PersistentDb } from './persistent-db';
import { createPersistentState } from './persistent-state';
import { createPersistentStore } from './persistent-store';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '..', '..');
const DEFAULT_MODEL_PATH = join(ROOT_DIR, '.models', 'gemma-3n-E2B-it-Q4_K_M.gguf');

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LiveBridgeOptions {
  /** Directory for persistent file-backed storage (db, store, state, files) */
  dataDir: string;
  /** Path to GGUF model file. Defaults to .models/gemma-3n-E2B-it-Q4_K_M.gguf */
  modelPath?: string;
  /** Set to false to skip model loading even if the file exists */
  loadModel?: boolean;
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
 * - db/store/state/data: persistent file-backed storage in dataDir
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

  // Store — persistent JSON file
  const pStore = createPersistentStore(join(dataDir, 'store.json'));
  const store = {
    get: (key: string): unknown => pStore.get(key),
    set: (key: string, value: unknown): void => pStore.set(key, value),
    delete: (key: string): void => pStore.delete(key),
    keys: (): string[] => pStore.keys(),
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

  // State — persistent JSON file with __getAll for debugging
  const stateFilePath = join(dataDir, 'state.json');
  const pState = createPersistentState(stateFilePath);
  const stateApi = {
    get: (key: string): unknown => pState.get(key),
    set: (key: string, value: unknown): void => pState.set(key, value),
    setPartial: (partial: Record<string, unknown>): void => pState.setPartial(partial),
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

  // Model — real local LLM via ModelBridge (Worker + SharedArrayBuffer)
  let modelBridge: ModelBridge | null = null;
  const resolvedModelPath = options.modelPath ?? DEFAULT_MODEL_PATH;
  const shouldLoadModel = options.loadModel !== false && existsSync(resolvedModelPath);

  if (shouldLoadModel) {
    globalThis.console.log(`[bootstrap-live] Loading model: ${resolvedModelPath}`);
    modelBridge = new ModelBridge();
    try {
      await modelBridge.load(resolvedModelPath);
      globalThis.console.log('[bootstrap-live] Model loaded successfully');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      globalThis.console.warn(`[bootstrap-live] Model failed to load: ${msg}`);
      modelBridge = null;
    }
  } else if (options.loadModel !== false) {
    globalThis.console.log(
      `[bootstrap-live] Model not found at ${resolvedModelPath} — model API disabled`,
    );
    globalThis.console.log(
      '[bootstrap-live] Run `yarn model:download` to enable local inference',
    );
  }

  const model = {
    isAvailable: (): boolean => modelBridge?.isAvailable() ?? false,
    getStatus: (): Record<string, unknown> =>
      modelBridge?.getStatus() ?? {
        available: false,
        loaded: false,
        loading: false,
        downloaded: existsSync(resolvedModelPath),
      },
    generate: (prompt: string, _options?: unknown): string => {
      if (!modelBridge || !modelBridge.isAvailable()) {
        throw new Error(
          'Model not available. Run `yarn model:download` and restart.',
        );
      }
      return modelBridge.generate(prompt, _options as ModelGenerateOptions | undefined);
    },
    summarize: (text: string, _options?: unknown): string => {
      if (!modelBridge || !modelBridge.isAvailable()) {
        throw new Error(
          'Model not available. Run `yarn model:download` and restart.',
        );
      }
      return modelBridge.summarize(text, _options as ModelSummarizeOptions | undefined);
    },
    submitSummary: (_submission: Record<string, unknown>): void => {
      globalThis.console.log(
        `[model.submitSummary] "${String((_submission as Record<string, string>).summary ?? '').substring(0, 80)}"`,
      );
    },
  };

  // OAuth — credential management and authenticated API proxy
  // Backend endpoints used:
  //   GET  /auth/:provider/connect        → { oauthUrl, state }
  //   ALL  /proxy/by-id/:integrationId/*  → proxied API call
  //   DELETE /auth/integrations/:id        → revoke integration
  const oauth = {
    getCredential: (): unknown => oauthCredential,
    fetch: (
      path: string,
      fetchOpts?: {
        method?: string;
        headers?: Record<string, string>;
        body?: string;
        timeout?: number;
        baseUrl?: string;
      },
    ): { status: number; headers: Record<string, string>; body: string } => {
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
      return realFetch(proxyUrl, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(jwtToken ? { Authorization: `Bearer ${jwtToken}` } : {}),
          ...(fetchOpts?.headers ?? {}),
        },
        body: fetchOpts?.body,
        timeout: fetchOpts?.timeout ? fetchOpts.timeout * 1000 : 30000,
      });
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

  // Timers — tracked in live state for manual triggering
  const setTimeout = (callback: () => void, delay = 0): number => {
    const id = liveState.nextTimerId++;
    liveState.timers.set(id, {
      callback,
      delay,
      isInterval: false,
      scheduledAt: Date.now(),
    });
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
    return id;
  };

  const clearTimeout = (id: number): void => {
    liveState.timers.delete(id);
  };

  const clearInterval = (id: number): void => {
    liveState.timers.delete(id);
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

  // WebSocket via ws npm package
  let RealWebSocket: unknown;
  try {
    const wsModule = await import('ws');
    RealWebSocket = wsModule.default || wsModule.WebSocket;
    globalThis.console.log('[bootstrap-live] Using ws npm package for WebSocket');
  } catch {
    RealWebSocket = globalThis.WebSocket;
    globalThis.console.log(
      '[bootstrap-live] Using native WebSocket (ws package not available)',
    );
  }

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
    store,
    db,
    net,
    platform,
    backend,
    socket: socketApi,
    state: stateApi,
    data,
    cron,
    skills,
    model,
    oauth,
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
    // Cleanup hook for persistent DB, model, and socket
    __cleanup: () => {
      if (socket) {
        socket.disconnect();
        socket = null;
      }
      if (modelBridge) {
        modelBridge.dispose().catch(() => {});
        modelBridge = null;
      }
      if (persistentDb) {
        persistentDb.close();
        persistentDb = null;
      }
    },
  };
}
