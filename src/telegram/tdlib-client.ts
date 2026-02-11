/**
 * TDLib Client Wrapper for Telegram Skill
 *
 * Provides a unified interface for TDLib access on both desktop (V8 ops) and Android (Tauri invoke).
 * This wrapper abstracts the platform differences and provides a consistent async API.
 */

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * TDLib request object with @type field.
 */
export interface TdRequest {
  '@type': string;
  [key: string]: unknown;
}

/**
 * TDLib ops interface exposed by V8 runtime bootstrap.
 */
interface TdLibOps {
  isAvailable: () => boolean;
  ensureInitialized: (dataDir: string) => Promise<number>;
  createClient: (dataDir: string) => Promise<number>;
  send: (requestJson: string) => Promise<string>;
  receive: (timeoutMs: number) => Promise<TdUpdate | null>;
  destroy: () => Promise<void>;
}

/**
 * Tauri internals interface for invoke.
 */
interface TauriInternals {
  invoke: <T>(cmd: string, args: Record<string, unknown>) => Promise<T>;
}

// Global type declarations
declare global {
  var tdlib: TdLibOps | undefined;

  var __TAURI_INTERNALS__: TauriInternals | undefined;
}

/**
 * TDLib response object.
 */
export interface TdResponse {
  '@type': string;
  [key: string]: unknown;
}

/**
 * TDLib error response.
 */
export interface TdError extends TdResponse {
  '@type': 'error';
  code: number;
  message: string;
}

/**
 * TDLib update types.
 */
export interface TdUpdate extends TdResponse {
  '@type': `update${string}`;
}

/**
 * TDLib user object.
 */
export interface TdUser {
  '@type': 'user';
  id: number;
  first_name: string;
  last_name?: string;
  usernames?: { active_usernames: string[] };
  phone_number?: string;
  is_verified?: boolean;
  is_premium?: boolean;
}

/**
 * TDLib authorization state types.
 */
export type TdAuthorizationState =
  | { '@type': 'authorizationStateWaitTdlibParameters' }
  | { '@type': 'authorizationStateWaitPhoneNumber' }
  | { '@type': 'authorizationStateWaitCode'; code_info?: unknown }
  | { '@type': 'authorizationStateWaitPassword'; password_hint?: string }
  | { '@type': 'authorizationStateReady' }
  | { '@type': 'authorizationStateClosed' };

/**
 * Update handler function type.
 */
export type UpdateHandler = (update: TdUpdate) => void;

// ============================================================================
// Platform Detection
// ============================================================================

/**
 * Check if TDLib ops are available (V8 runtime on desktop).
 */
function isTdLibOpsAvailable(): boolean {
  try {
    return (
      typeof globalThis.tdlib !== 'undefined' &&
      typeof globalThis.tdlib.isAvailable === 'function' &&
      globalThis.tdlib.isAvailable()
    );
  } catch {
    return false;
  }
}

/**
 * Check if Tauri invoke is available (Android/mobile).
 */
function isTauriInvokeAvailable(): boolean {
  try {
    return (
      typeof globalThis.__TAURI_INTERNALS__ !== 'undefined' &&
      typeof globalThis.__TAURI_INTERNALS__.invoke === 'function'
    );
  } catch {
    return false;
  }
}

// ============================================================================
// TDLib Client Class
// ============================================================================

/**
 * Unified TDLib client wrapper.
 *
 * Provides the same API on both desktop (V8 ops) and Android (Tauri invoke).
 *
 * Usage:
 * ```typescript
 * const client = new TdLibClient();
 * await client.init('/path/to/data');
 *

 * // Get current user
 * const user = await client.send({ '@type': 'getMe' });
 *
 * // Start receiving updates
 * client.startUpdateLoop((update) => {
 *   console.log('Update:', update);
 * });
 *
 * // Cleanup
 * await client.destroy();
 * ```
 */
export class TdLibClient {
  private clientId: number | null = null;
  private isInitialized = false;
  private updateHandler: UpdateHandler | null = null;
  private updateLoopRunning = false;
  private updateLoopAbort: AbortController | null = null;

  /** Timestamp (ms) until which requests are rate-limited. 0 = not limited. */
  private rateLimitedUntil = 0;

  /**
   * Check if TDLib is available on the current platform.
   */
  static isAvailable(): boolean {
    return isTdLibOpsAvailable() || isTauriInvokeAvailable();
  }

  /**
   * Initialize the TDLib client with the given data directory.
   *
   * @param dataDir - Path to store TDLib database and files.
   * @throws Error if TDLib is not available or initialization fails.
   */
  /**
   * Connect to the already-running TDLib client.
   *
   * The Rust side creates the client and sets parameters at app startup,
   * so this just marks the wrapper as ready to send/receive.
   *
   * @param _dataDir - Unused (kept for API compatibility). The Rust side
   *   determines the data directory at app startup.
   */
  async init(_dataDir?: string): Promise<void> {
    if (this.isInitialized) return; // idempotent

    if (!isTdLibOpsAvailable() && !isTauriInvokeAvailable()) {
      throw new Error('TDLib is not available on this platform');
    }

    // The Rust singleton always uses client ID 1.
    this.clientId = 1;
    this.isInitialized = true;
    console.log('[tdlib-client] Connected to existing TDLib client');
  }

  /**
   * Send a TDLib request and wait for the response.
   *
   * @param request - TDLib API request object with @type field.
   * @returns TDLib response object.
   * @throws Error if TDLib is not initialized or request fails.
   */
  async send<T extends TdResponse = TdResponse>(request: TdRequest): Promise<T> {
    if (!this.isInitialized) {
      throw new Error('TDLib client not initialized');
    }

    // Check if we're currently rate-limited
    if (this.rateLimitedUntil > 0) {
      const remaining = this.rateLimitedUntil - Date.now();
      if (remaining > 0) {
        const secs = Math.ceil(remaining / 1000);
        throw new Error(
          `Rate limited: too many requests. Please wait ${secs}s before retrying. ` +
            `(Request: ${request['@type']})`
        );
      }
      // Cooldown expired, clear it
      this.rateLimitedUntil = 0;
    }

    console.log('[tdlib-client] Sending request:', request);

    let response: T;

    if (isTdLibOpsAvailable() && globalThis.tdlib) {
      // Desktop: use V8 ops - serialize to JSON string as expected by Rust bridge
      const requestJson = JSON.stringify(request);
      const responseJson = await globalThis.tdlib.send(requestJson);
      response = JSON.parse(responseJson) as T;
    } else if (isTauriInvokeAvailable() && globalThis.__TAURI_INTERNALS__) {
      // Android: use Tauri invoke
      response = await globalThis.__TAURI_INTERNALS__.invoke<T>('tdlib_send', { request });
    } else {
      throw new Error('TDLib is not available on this platform');
    }

    // Check for error response
    if (response['@type'] === 'error') {
      const error = response as unknown as TdError;

      // Handle FLOOD_WAIT / 429 Too Many Requests
      if (error.code === 429) {
        const retryAfterSecs = this.parseRetryAfter(error.message);
        this.rateLimitedUntil = Date.now() + retryAfterSecs * 1000;
        console.warn(
          `[tdlib-client] Rate limited for ${retryAfterSecs}s (request: ${request['@type']})`
        );
        throw new Error(
          `Rate limited: too many requests. Please wait ${retryAfterSecs}s before retrying. ` +
            `(Request: ${request['@type']})`
        );
      }

      throw new Error(`TDLib error ${error.code}: ${error.message}`);
    }

    return response;
  }

  /**
   * Check if the client is currently rate-limited.
   */
  get isRateLimited(): boolean {
    return this.rateLimitedUntil > 0 && Date.now() < this.rateLimitedUntil;
  }

  /**
   * Get the number of seconds remaining on the rate limit, or 0 if not limited.
   */
  get rateLimitRemaining(): number {
    if (this.rateLimitedUntil <= 0) return 0;
    const remaining = Math.ceil((this.rateLimitedUntil - Date.now()) / 1000);
    return remaining > 0 ? remaining : 0;
  }

  /**
   * Receive the next update from TDLib (with timeout).
   *
   * @param timeoutMs - Timeout in milliseconds (default: 1000).
   * @returns Update object or null if timeout.
   */
  async receive(timeoutMs = 1000): Promise<TdUpdate | null> {
    if (!this.isInitialized) {
      return null;
    }

    if (isTdLibOpsAvailable() && globalThis.tdlib) {
      // Desktop: use V8 ops
      return await globalThis.tdlib.receive(timeoutMs);
    } else if (isTauriInvokeAvailable() && globalThis.__TAURI_INTERNALS__) {
      // Android: use Tauri invoke
      return await globalThis.__TAURI_INTERNALS__.invoke<TdUpdate | null>('tdlib_receive', {
        timeoutMs,
      });
    }

    return null;
  }

  /**
   * Start the update receiving loop.
   *
   * @param handler - Function to call for each update.
   */
  startUpdateLoop(handler: UpdateHandler): void {
    if (this.updateLoopRunning) {
      console.warn('[tdlib-client] Update loop already running');
      return;
    }

    this.updateHandler = handler;
    this.updateLoopRunning = true;
    this.updateLoopAbort = new AbortController();

    this.runUpdateLoop();
  }

  /**
   * Stop the update receiving loop.
   */
  stopUpdateLoop(): void {
    this.updateLoopRunning = false;
    this.updateLoopAbort?.abort();
    this.updateLoopAbort = null;
    this.updateHandler = null;
  }

  /**
   * Internal update loop.
   */
  private async runUpdateLoop(): Promise<void> {
    while (this.updateLoopRunning) {
      try {
        const update = await this.receive(100);
        if (update && this.updateHandler) {
          try {
            this.updateHandler(update);
          } catch (e) {
            console.error('[tdlib-client] Update handler error:', e);
          }
        }
      } catch (e) {
        if (this.updateLoopRunning) {
          console.error('[tdlib-client] Update loop error:', e);
        }
      }

      // Small delay to prevent busy-spinning
      await this.sleep(10);
    }
  }

  /**
   * Destroy the TDLib client and clean up resources.
   */
  async destroy(): Promise<void> {
    if (!this.isInitialized) {
      return;
    }

    // Stop update loop first
    this.stopUpdateLoop();

    if (isTdLibOpsAvailable() && globalThis.tdlib) {
      // Desktop: use V8 ops
      await globalThis.tdlib.destroy();
    } else if (isTauriInvokeAvailable() && globalThis.__TAURI_INTERNALS__) {
      // Android: use Tauri invoke
      await globalThis.__TAURI_INTERNALS__.invoke<void>('tdlib_destroy', {});
    }

    this.clientId = null;
    this.isInitialized = false;
    console.log('[tdlib-client] Destroyed');
  }

  /**
   * Check if the client is initialized.
   */
  get initialized(): boolean {
    return this.isInitialized;
  }

  /**
   * Get the client ID.
   */
  get id(): number | null {
    return this.clientId;
  }

  // ============================================================================
  // Helper Methods
  // ============================================================================

  /**
   * Sleep for a given number of milliseconds.
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Parse the retry-after seconds from a TDLib 429 error message.
   * Format: "Too Many Requests: retry after N"
   * Falls back to 30s if parsing fails.
   */
  private parseRetryAfter(message: string): number {
    const match = message.match(/retry after (\d+)/i);
    if (match) {
      const seconds = parseInt(match[1], 10);
      if (seconds > 0) return seconds;
    }
    return 30; // Fallback: 30 seconds
  }

  // ============================================================================
  // Convenience Methods for Common Operations
  // ============================================================================

  /**
   * Set authentication phone number.
   */
  async setAuthenticationPhoneNumber(phoneNumber: string): Promise<void> {
    await this.send({
      '@type': 'setAuthenticationPhoneNumber',
      phone_number: phoneNumber,
      settings: {
        '@type': 'phoneNumberAuthenticationSettings',
        allow_flash_call: false,
        allow_missed_call: false,
        is_current_phone_number: false,
        has_unknown_phone_number: false,
        allow_sms_retriever_api: false,
      },
    });
  }

  /**
   * Check authentication code.
   */
  async checkAuthenticationCode(code: string): Promise<void> {
    await this.send({ '@type': 'checkAuthenticationCode', code });
  }

  /**
   * Check authentication password (2FA).
   */
  async checkAuthenticationPassword(password: string): Promise<void> {
    await this.send({ '@type': 'checkAuthenticationPassword', password });
  }

  /**
   * Get the current user.
   */
  async getMe(): Promise<TdUser> {
    const response = await this.send({ '@type': 'getMe' });
    return response as unknown as TdUser;
  }

  /**
   * Log out from the current session.
   */
  async logOut(): Promise<void> {
    await this.send({ '@type': 'logOut' });
  }

  /**
   * Close TDLib (graceful shutdown).
   */
  async close(): Promise<void> {
    await this.send({ '@type': 'close' });
  }
}

// ============================================================================
// Global Export
// ============================================================================

// Make TdLibClient available globally for the skill
(globalThis as Record<string, unknown>).TdLibClient = TdLibClient;

// Export for module usage
export default TdLibClient;
