/**
 * tdlib-bridge.ts - Real TDLib bridge for the Node.js test harness
 *
 * Uses koffi (modern Node.js FFI) to call TDLib's C JSON Client API directly,
 * with prebuilt-tdlib supplying the shared library binary.
 *
 * TDLib's C API:
 *   int    td_create_client_id()
 *   void   td_send(int client_id, const char* request)
 *   char*  td_receive(double timeout)          // returns JSON for ANY client
 *   char*  td_execute(const char* request)     // synchronous, no client needed
 *
 * This bridge implements the TdLibOps interface expected by the skill:
 *   isAvailable()               → boolean
 *   createClient(dataDir)       → Promise<number>
 *   send(requestJson)           → Promise<string>
 *   receive(timeoutMs)          → Promise<TdUpdate | null>
 *   destroy()                   → Promise<void>
 */

import { createRequire } from 'module';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TdUpdate {
  '@type': string;
  [key: string]: unknown;
}

interface TdLibFFI {
  td_create_client_id: () => number;
  td_send: (clientId: number, request: string) => void;
  td_receive: (timeout: number) => string | null;
  td_execute: (request: string) => string | null;
}

interface PendingRequest {
  resolve: (value: string) => void;
  reject: (reason: Error) => void;
}

// ---------------------------------------------------------------------------
// TDLib Bridge
// ---------------------------------------------------------------------------

export class TdLibBridge {
  private ffi: TdLibFFI | null = null;
  private clientId: number = -1;
  private available = false;

  // Request-response correlation via @extra
  private extraCounter = 0;
  private pendingRequests = new Map<string, PendingRequest>();

  // Update queue for receive() callers
  private updateQueue: TdUpdate[] = [];
  private updateWaiters: Array<{
    resolve: (value: TdUpdate | null) => void;
    timer: ReturnType<typeof setTimeout>;
  }> = [];

  // Poll loop
  private pollInterval: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.loadFFI();
  }

  /** Attempt to load koffi + prebuilt-tdlib. Failures just set available=false. */
  private loadFFI(): void {
    try {
      // Use createRequire for ESM compatibility — bare require() is not available
      // when running under tsx/ESM. createRequire gives us a CJS-compatible require
      // that can load native .node addons (koffi) and platform binaries (prebuilt-tdlib).
      const esmRequire = createRequire(import.meta.url);
      const koffi = esmRequire('koffi');
      const { getTdjson } = esmRequire('prebuilt-tdlib');

      const libPath: string = getTdjson();
      const lib = koffi.load(libPath);

      this.ffi = {
        td_create_client_id: lib.func('td_create_client_id', 'int', []),
        td_send: lib.func('td_send', 'void', ['int', 'string']),
        td_receive: lib.func('td_receive', 'string', ['double']),
        td_execute: lib.func('td_execute', 'string', ['string']),
      };

      // Reduce TDLib's own logging verbosity (default is very chatty)
      // Level 0 = fatal, 1 = error, 2 = warning, 3 = info, 4+ = debug
      this.ffi.td_execute(
        JSON.stringify({
          '@type': 'setLogVerbosityLevel',
          new_verbosity_level: 1,
        }),
      );

      // Quick smoke test: td_execute with getOption should work without a client
      const testResult = this.ffi.td_execute(
        JSON.stringify({ '@type': 'getOption', name: 'version' }),
      );
      if (testResult) {
        const parsed = JSON.parse(testResult);
        if (parsed['@type'] === 'optionValueString') {
          globalThis.console.log(`[tdlib-bridge] TDLib ${parsed.value} loaded successfully`);
        }
      }

      this.available = true;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      // Only log if the error isn't just "module not found"
      if (!msg.includes('Cannot find module')) {
        globalThis.console.warn(`[tdlib-bridge] Failed to load TDLib: ${msg}`);
      } else {
        globalThis.console.log(
          '[tdlib-bridge] koffi or prebuilt-tdlib not installed — TDLib unavailable',
        );
      }
      this.available = false;
    }
  }

  /** Whether the TDLib FFI is loaded and functional. */
  isAvailable(): boolean {
    return this.available;
  }

  /**
   * Create a new TDLib client and start the poll loop.
   * @param _dataDir - Data directory (passed for interface compat; TDLib parameters are sent via setTdlibParameters)
   * @returns The client ID
   */
  async createClient(_dataDir: string): Promise<number> {
    if (!this.ffi) throw new Error('TDLib not available');
    if (this.clientId >= 0) throw new Error('Client already created — call destroy() first');

    this.clientId = this.ffi.td_create_client_id();
    globalThis.console.log(`[tdlib-bridge] Created client ID: ${this.clientId}`);

    // Start polling for responses/updates
    this.startPollLoop();

    return this.clientId;
  }

  /**
   * Ensure a TDLib client is initialized: create if needed, then send
   * setTdlibParameters. Mirrors the Rust-side ensureInitialized which creates
   * the client and reactively sends parameters in one call.
   *
   * @param dataDir - Data directory for TDLib storage.
   * @returns The client ID.
   */
  async ensureInitialized(dataDir: string): Promise<number> {
    if (!this.ffi) throw new Error('TDLib not available');

    // If client already exists, return its ID
    if (this.clientId >= 0) return this.clientId;

    // Create the client
    const clientId = await this.createClient(dataDir);

    // Auto-send setTdlibParameters (mirrors Rust-side behavior).
    // The Rust side hardcodes API_ID/API_HASH; here we use env vars or defaults.
    const apiId = parseInt(process.env.TELEGRAM_API_ID || '28685916', 10);
    const apiHash = process.env.TELEGRAM_API_HASH || 'd540ab21dece5404af298c44f4f6386d';

    const params = JSON.stringify({
      '@type': 'setTdlibParameters',
      database_directory: dataDir,
      use_file_database: true,
      use_chat_info_database: true,
      use_message_database: true,
      use_secret_chats: false,
      api_id: apiId,
      api_hash: apiHash,
      system_language_code: 'en',
      device_model: 'Node.js Test Harness',
      system_version: process.version,
      application_version: '1.0.0',
    });

    // Send directly (not via the correlated send() method, since TDLib
    // may already be waiting for parameters and respond via an update).
    this.ffi.td_send(clientId, params);
    globalThis.console.log('[tdlib-bridge] Sent setTdlibParameters');

    return clientId;
  }

  /**
   * Send a TDLib request and wait for the response.
   * Injects @extra for request-response correlation.
   */
  async send(requestJson: string): Promise<string> {
    if (!this.ffi) throw new Error('TDLib not available');
    if (this.clientId < 0) throw new Error('Client not created');

    const request = JSON.parse(requestJson);
    const extra = String(++this.extraCounter);
    request['@extra'] = extra;

    globalThis.console.log(`[tdlib-bridge] send: ${request['@type']} @extra=${extra}`);

    return new Promise<string>((resolve, reject) => {
      // Set up a 30-second timeout for the response
      const timer = setTimeout(() => {
        this.pendingRequests.delete(extra);
        reject(new Error(`TDLib request timed out after 30s: ${request['@type']}`));
      }, 30000);

      this.pendingRequests.set(extra, {
        resolve: (value: string) => {
          clearTimeout(timer);
          resolve(value);
        },
        reject: (reason: Error) => {
          clearTimeout(timer);
          reject(reason);
        },
      });

      this.ffi!.td_send(this.clientId, JSON.stringify(request));
    });
  }

  /**
   * Receive the next update from TDLib (not a response to a send() call).
   * Returns null if no update arrives within timeoutMs.
   */
  async receive(timeoutMs: number): Promise<TdUpdate | null> {
    // Check the queue first
    if (this.updateQueue.length > 0) {
      return this.updateQueue.shift()!;
    }

    // Wait for the next update with timeout
    return new Promise<TdUpdate | null>((resolve) => {
      const timer = setTimeout(() => {
        // Remove this waiter and resolve null
        this.updateWaiters = this.updateWaiters.filter((w) => w.timer !== timer);
        resolve(null);
      }, timeoutMs);

      this.updateWaiters.push({ resolve, timer });
    });
  }

  /**
   * Stop the poll loop, send close, reject pending requests, clean up.
   */
  async destroy(): Promise<void> {
    // Stop poll loop first
    this.stopPollLoop();

    // Send close request if we have a valid client
    if (this.ffi && this.clientId >= 0) {
      try {
        this.ffi.td_send(
          this.clientId,
          JSON.stringify({ '@type': 'close' }),
        );
        // Drain remaining messages for a short period to let TDLib shut down
        for (let i = 0; i < 50; i++) {
          const raw = this.ffi.td_receive(0.1);
          if (!raw) continue;
          try {
            const msg = JSON.parse(raw);
            if (
              msg['@type'] === 'updateAuthorizationState' &&
              msg.authorization_state?.['@type'] === 'authorizationStateClosed'
            ) {
              break;
            }
          } catch {
            // ignore parse errors during shutdown
          }
        }
      } catch {
        // best effort
      }
    }

    // Reject all pending requests
    for (const [extra, pending] of this.pendingRequests) {
      pending.reject(new Error('TDLib client destroyed'));
      this.pendingRequests.delete(extra);
    }

    // Resolve all update waiters with null
    for (const waiter of this.updateWaiters) {
      clearTimeout(waiter.timer);
      waiter.resolve(null);
    }
    this.updateWaiters = [];
    this.updateQueue = [];

    this.clientId = -1;
    globalThis.console.log('[tdlib-bridge] Client destroyed');
  }

  // ─── Poll Loop ──────────────────────────────────────────────────

  private startPollLoop(): void {
    if (this.pollInterval) return;

    this.pollInterval = setInterval(() => {
      this.drainMessages();
    }, 50);
  }

  private stopPollLoop(): void {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  /**
   * Drain all available messages from td_receive (non-blocking).
   * Routes responses to pending requests, updates to the update queue/waiters.
   */
  private drainMessages(): void {
    if (!this.ffi) return;

    // Drain up to 100 messages per tick to avoid infinite loop
    for (let i = 0; i < 100; i++) {
      const raw = this.ffi.td_receive(0); // non-blocking
      if (!raw) break;

      let msg: Record<string, unknown>;
      try {
        msg = JSON.parse(raw);
      } catch {
        globalThis.console.warn('[tdlib-bridge] Failed to parse TDLib response:', raw);
        continue;
      }

      const msgType = msg['@type'] as string;

      // Filter by client ID — TDLib tags all responses
      const msgClientId = msg['@client_id'] as number | undefined;
      if (msgClientId !== undefined && msgClientId !== this.clientId) {
        continue; // Not for our client
      }

      // Log significant messages for debugging
      if (msgType === 'error' || msgType === 'updateAuthorizationState' || msgType === 'ok') {
        const authState = (msg as { authorization_state?: { '@type'?: string } }).authorization_state?.['@type'];
        globalThis.console.log(
          `[tdlib-bridge] ${msgType}${authState ? ` (${authState})` : ''}${msg['@extra'] ? ` @extra=${msg['@extra']}` : ''}${msgType === 'error' ? ` code=${msg.code} msg=${msg.message}` : ''}`,
        );
      }

      // Check if this is a response to a pending send() request
      const extra = msg['@extra'] as string | undefined;
      if (extra && this.pendingRequests.has(extra)) {
        const pending = this.pendingRequests.get(extra)!;
        this.pendingRequests.delete(extra);
        // Remove @extra and @client_id from the response before returning
        delete msg['@extra'];
        delete msg['@client_id'];
        pending.resolve(JSON.stringify(msg));
        continue;
      }

      // Remove internal fields
      delete msg['@client_id'];

      // This is an update — route to waiters or queue
      const update = msg as TdUpdate;
      if (this.updateWaiters.length > 0) {
        const waiter = this.updateWaiters.shift()!;
        clearTimeout(waiter.timer);
        waiter.resolve(update);
      } else {
        this.updateQueue.push(update);
      }
    }
  }
}
