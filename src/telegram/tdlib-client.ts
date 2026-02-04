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
  createClient: (dataDir: string) => Promise<number>;
  send: <T>(request: TdRequest) => Promise<T>;
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
  // eslint-disable-next-line no-var
  var tdlib: TdLibOps | undefined;
  // eslint-disable-next-line no-var
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
  usernames?: {
    active_usernames: string[];
  };
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
    return typeof globalThis.tdlib !== 'undefined' &&
      typeof globalThis.tdlib.isAvailable === 'function' &&
      globalThis.tdlib.isAvailable();
  } catch {
    return false;
  }
}

/**
 * Check if Tauri invoke is available (Android/mobile).
 */
function isTauriInvokeAvailable(): boolean {
  try {
    return typeof globalThis.__TAURI_INTERNALS__ !== 'undefined' &&
      typeof globalThis.__TAURI_INTERNALS__.invoke === 'function';
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
 * // Send setTdlibParameters
 * await client.send({
 *   '@type': 'setTdlibParameters',
 *   api_id: 12345,
 *   api_hash: 'your_hash',
 *   // ...other params
 * });
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
  async init(dataDir: string): Promise<void> {
    if (this.isInitialized) {
      throw new Error('TDLib client already initialized');
    }

    if (isTdLibOpsAvailable() && globalThis.tdlib) {
      // Desktop: use V8 ops
      this.clientId = await globalThis.tdlib.createClient(dataDir);
    } else if (isTauriInvokeAvailable() && globalThis.__TAURI_INTERNALS__) {
      // Android: use Tauri invoke
      this.clientId = await globalThis.__TAURI_INTERNALS__.invoke<number>('tdlib_create_client', { dataDir });
    } else {
      throw new Error('TDLib is not available on this platform');
    }

    this.isInitialized = true;
    console.log('[tdlib-client] Initialized with client ID:', this.clientId);
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

    let response: T;

    if (isTdLibOpsAvailable() && globalThis.tdlib) {
      // Desktop: use V8 ops
      response = await globalThis.tdlib.send<T>(request);
    } else if (isTauriInvokeAvailable() && globalThis.__TAURI_INTERNALS__) {
      // Android: use Tauri invoke
      response = await globalThis.__TAURI_INTERNALS__.invoke<T>('tdlib_send', { request });
    } else {
      throw new Error('TDLib is not available on this platform');
    }

    // Check for error response
    if (response['@type'] === 'error') {
      const error = response as unknown as TdError;
      throw new Error(`TDLib error ${error.code}: ${error.message}`);
    }

    return response;
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
      return await globalThis.__TAURI_INTERNALS__.invoke<TdUpdate | null>('tdlib_receive', { timeoutMs });
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
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // ============================================================================
  // Convenience Methods for Common Operations
  // ============================================================================

  /**
   * Set TDLib parameters. Must be called after init() and before authentication.
   */
  async setTdlibParameters(params: {
    api_id: number;
    api_hash: string;
    database_directory?: string;
    files_directory?: string;
    use_message_database?: boolean;
    use_secret_chats?: boolean;
    system_language_code?: string;
    device_model?: string;
    application_version?: string;
  }): Promise<void> {
    await this.send({
      '@type': 'setTdlibParameters',
      use_test_dc: false,
      database_directory: params.database_directory || '',
      files_directory: params.files_directory || '',
      database_encryption_key: '',
      use_file_database: true,
      use_chat_info_database: true,
      use_message_database: params.use_message_database ?? true,
      use_secret_chats: params.use_secret_chats ?? false,
      api_id: params.api_id,
      api_hash: params.api_hash,
      system_language_code: params.system_language_code ?? 'en',
      device_model: params.device_model ?? 'Desktop',
      system_version: '',
      application_version: params.application_version ?? '1.0.0',
    });
  }

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
    await this.send({
      '@type': 'checkAuthenticationCode',
      code,
    });
  }

  /**
   * Check authentication password (2FA).
   */
  async checkAuthenticationPassword(password: string): Promise<void> {
    await this.send({
      '@type': 'checkAuthenticationPassword',
      password,
    });
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
