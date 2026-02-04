/**
 * bootstrap.ts - Provides the same globals as Rust's bootstrap.js
 *
 * Creates all the bridge APIs (db, store, net, platform, state, data, cron, skills)
 * with mock implementations backed by mock-state.ts.
 */

import { dbAll, dbExec, dbGet, dbKvGet, dbKvSet } from './mock-db.ts';
import { getMockState, type FetchOptions } from './mock-state.ts';

/**
 * Create all bridge API globals and inject them into the provided context
 */
export async function createBridgeAPIs(): Promise<Record<string, unknown>> {
  const state = getMockState();

  // Console - logs to mock state for inspection
  const console = {
    log: (...args: unknown[]) => {
      const message = args.map(String).join(' ');
      state.consoleOutput.push({ level: 'log', message });
      // Also print to real console for visibility during script execution
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
  const store = {
    get: (key: string): unknown => {
      return state.store[key] ?? null;
    },
    set: (key: string, value: unknown): void => {
      state.store[key] = value;
    },
    delete: (key: string): void => {
      delete state.store[key];
    },
    keys: (): string[] => {
      return Object.keys(state.store);
    },
  };

  // Database API - SQLite mock
  const db = {
    exec: (sql: string, params?: unknown[]): void => {
      dbExec(sql, params ?? []);
    },
    get: (sql: string, params?: unknown[]): Record<string, unknown> | null => {
      return dbGet(sql, params ?? []);
    },
    all: (sql: string, params?: unknown[]): Array<Record<string, unknown>> => {
      return dbAll(sql, params ?? []);
    },
    kvGet: (key: string): unknown => {
      return dbKvGet(key);
    },
    kvSet: (key: string, value: unknown): void => {
      dbKvSet(key, value);
    },
  };

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
  const stateApi = {
    get: (key: string): unknown => {
      return state.state[key];
    },
    set: (key: string, value: unknown): void => {
      state.state[key] = value;
    },
    setPartial: (partial: Record<string, unknown>): void => {
      Object.assign(state.state, partial);
    },
  };

  // Data API - file I/O mock
  const data = {
    read: (filename: string): string | null => {
      return state.dataFiles[filename] ?? null;
    },
    write: (filename: string, content: string): void => {
      state.dataFiles[filename] = content;
    },
  };

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
      // Mock: would require loading other skills
      return { error: 'Inter-skill calls not supported in test harness' };
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

  // Mock window.location for gramjs browser detection
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

  // Mock event listeners storage for browser API compatibility (gramjs uses these for offline detection)
  const mockEventListeners: Map<string, Set<EventListener>> = new Map();

  // Mock window event methods
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

  // Try to use the 'ws' npm package for WebSocket (more compatible with Telegram)
  // Falls back to Deno's native WebSocket if not available
  let RealWebSocket: typeof WebSocket;
  try {
    // Dynamic import of ws package (available via npm in Deno 2+)
    // @ts-ignore - dynamic npm import
    const wsModule = await import('npm:ws');
    RealWebSocket = wsModule.default || wsModule.WebSocket;
    globalThis.console.log('[bootstrap] Using ws npm package for WebSocket');
  } catch {
    // Fallback to Deno's native WebSocket
    RealWebSocket = globalThis.WebSocket;
    globalThis.console.log('[bootstrap] Using native Deno WebSocket');
  }

  // Mock crypto for gramjs cryptography
  const mockCrypto = {
    getRandomValues: <T extends ArrayBufferView>(array: T): T => {
      // Use Deno's crypto for actual randomness
      if (typeof globalThis.crypto !== 'undefined' && globalThis.crypto.getRandomValues) {
        return globalThis.crypto.getRandomValues(array);
      }
      // Fallback: fill with pseudo-random values
      if (array instanceof Uint8Array) {
        for (let i = 0; i < array.length; i++) {
          array[i] = Math.floor(Math.random() * 256);
        }
      }
      return array;
    },
    subtle: typeof globalThis.crypto !== 'undefined' ? globalThis.crypto.subtle : undefined,
    randomUUID:
      typeof globalThis.crypto !== 'undefined' && globalThis.crypto.randomUUID
        ? () => globalThis.crypto.randomUUID()
        : () => {
            // Simple UUID v4 fallback
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
              const r = (Math.random() * 16) | 0;
              const v = c === 'x' ? r : (r & 0x3) | 0x8;
              return v.toString(16);
            });
          },
  };

  // Mock Buffer class for gramjs (simplified)
  class MockBuffer extends Uint8Array {
    static isBuffer(obj: unknown): obj is MockBuffer {
      return obj instanceof MockBuffer || obj instanceof Uint8Array;
    }

    static from(
      data: string | ArrayLike<number> | ArrayBufferLike,
      encoding?: string
    ): MockBuffer {
      if (typeof data === 'string') {
        if (encoding === 'base64') {
          const binaryString = atob(data);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          return new MockBuffer(bytes);
        }
        // Default to utf-8
        const encoder = new TextEncoder();
        return new MockBuffer(encoder.encode(data));
      }
      if (data instanceof ArrayBuffer) {
        return new MockBuffer(new Uint8Array(data));
      }
      return new MockBuffer(data as ArrayLike<number>);
    }

    static alloc(size: number, fill?: number): MockBuffer {
      const buf = new MockBuffer(size);
      if (fill !== undefined) {
        buf.fill(fill);
      }
      return buf;
    }

    static allocUnsafe(size: number): MockBuffer {
      return new MockBuffer(size);
    }

    static concat(list: Uint8Array[], totalLength?: number): MockBuffer {
      const length = totalLength ?? list.reduce((acc, arr) => acc + arr.length, 0);
      const result = new MockBuffer(length);
      let offset = 0;
      for (const arr of list) {
        result.set(arr, offset);
        offset += arr.length;
      }
      return result;
    }

    toString(encoding?: string): string {
      if (encoding === 'base64') {
        let binary = '';
        for (let i = 0; i < this.length; i++) {
          binary += String.fromCharCode(this[i]);
        }
        return btoa(binary);
      }
      if (encoding === 'hex') {
        return Array.from(this)
          .map((b) => b.toString(16).padStart(2, '0'))
          .join('');
      }
      // Default to utf-8
      const decoder = new TextDecoder();
      return decoder.decode(this);
    }

    write(string: string, offset = 0, _length?: number, encoding?: string): number {
      const bytes = MockBuffer.from(string, encoding);
      this.set(bytes, offset);
      return bytes.length;
    }

    readUInt32BE(offset = 0): number {
      return (this[offset] << 24) | (this[offset + 1] << 16) | (this[offset + 2] << 8) | this[offset + 3];
    }

    readUInt32LE(offset = 0): number {
      return this[offset] | (this[offset + 1] << 8) | (this[offset + 2] << 16) | (this[offset + 3] << 24);
    }

    writeUInt32BE(value: number, offset = 0): number {
      this[offset] = (value >>> 24) & 0xff;
      this[offset + 1] = (value >>> 16) & 0xff;
      this[offset + 2] = (value >>> 8) & 0xff;
      this[offset + 3] = value & 0xff;
      return offset + 4;
    }

    writeUInt32LE(value: number, offset = 0): number {
      this[offset] = value & 0xff;
      this[offset + 1] = (value >>> 8) & 0xff;
      this[offset + 2] = (value >>> 16) & 0xff;
      this[offset + 3] = (value >>> 24) & 0xff;
      return offset + 4;
    }

    slice(start?: number, end?: number): MockBuffer {
      return new MockBuffer(super.slice(start, end));
    }

    subarray(start?: number, end?: number): MockBuffer {
      return new MockBuffer(super.subarray(start, end));
    }
  }

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
    btoa: (str: string): string => btoa(str),
    atob: (str: string): string => atob(str),
    // Browser-like globals for gramjs
    location: mockLocation,
    WebSocket: RealWebSocket,
    crypto: mockCrypto,
    Buffer: MockBuffer,
    // Browser event API mocks (gramjs uses these for offline detection)
    addEventListener,
    removeEventListener,
    dispatchEvent,
    navigator: {
      onLine: true,
      userAgent: 'Deno/1.0 (mock harness)',
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
  };
}
