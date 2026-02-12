// telegram/setup.ts
// Setup flow (onSetupStart, onSetupSubmit, onSetupCancel) for Telegram skill.
import {
  checkAuthenticationCode,
  checkAuthenticationPassword,
  setAuthenticationPhoneNumber,
} from './api/auth';
import './state';

// Access TdLibClient from globalThis (workaround for esbuild bundling issues)
const getTdLibClientClass = () => {
  const cls = (globalThis as any).TdLibClient;
  if (!cls) {
    throw new Error('TdLibClient not available on globalThis');
  }
  return cls;
};

export interface TelegramSetupDeps {
  initClient: () => Promise<void>;
  onError: (args: SkillErrorArgs) => void;
  publishState: () => void;
}

export function createSetupHandlers(deps: TelegramSetupDeps): {
  onSetupStart: () => Promise<SetupStartResult>;
  onSetupSubmit: (args: {
    stepId: string;
    values: Record<string, unknown>;
  }) => Promise<SetupSubmitResult>;
  onSetupCancel: () => Promise<void>;
} {
  const { initClient, onError, publishState } = deps;

  /**
   * Wait for auth state to change to one of the expected states.
   * Returns the new auth state or throws on timeout/error.
   * Uses progressive timeouts with better error messaging.
   *
   * NOTE: This function relies on the background update loop to process TDLib updates.
   * It does NOT poll client.receive() directly to avoid conflicts with the background loop.
   */
  async function waitForAuthStateChange(
    expectedStates: string[],
    totalTimeoutMs: number = 30000
  ): Promise<string> {
    const s = globalThis.getTelegramSkillState();
    if (!s.client) {
      throw new Error('TDLib client not initialized');
    }

    const startTime = Date.now();
    console.log(`[telegram] Waiting for auth state change to: ${expectedStates.join(', ')}, current: ${s.authState}`);

    // IMMEDIATE CHECK: State might have already changed via background update loop
    if (expectedStates.includes(s.authState)) {
      console.log(`[telegram] Auth state already at expected value: ${s.authState}`);
      return s.authState;
    }

    // Validate current auth state
    if (s.authState === 'unknown') {
      console.warn('[telegram] Warning: Auth state is "unknown" - this may indicate a connection issue');
    }

    // Progressive timeout checkpoints for better error messages
    const checkpoints = [
      { time: 5000, message: 'Still waiting for Telegram response (5s)...' },
      { time: 15000, message: 'Extended wait for Telegram response (15s)...' },
      { time: 25000, message: 'Long wait detected - possible connection issue (25s)...' }
    ];

    let lastCheckpointIndex = -1;

    // PASSIVE WAITING: Let background update loop handle TDLib updates
    // We just poll the state variable that gets updated by the background loop
    while (Date.now() - startTime < totalTimeoutMs) {
      const currentState = s.authState;
      const elapsedTime = Date.now() - startTime;

      // Check for expected states
      if (expectedStates.includes(currentState)) {
        console.log(`[telegram] Auth state changed to: ${currentState} (after ${elapsedTime}ms)`);
        return currentState;
      }

      // Log progress at checkpoints
      const currentCheckpointIndex = checkpoints.findIndex(cp => elapsedTime >= cp.time && elapsedTime < cp.time + 250);
      if (currentCheckpointIndex > lastCheckpointIndex && currentCheckpointIndex !== -1) {
        console.log(`[telegram] ${checkpoints[currentCheckpointIndex].message}`);
        console.log(`[telegram] Current state: ${currentState}, expected: ${expectedStates.join(', ')}`);
        lastCheckpointIndex = currentCheckpointIndex;
      }

      // Check for error conditions
      if (currentState === 'closed') {
        throw new Error('TDLib client connection closed unexpectedly during authentication');
      }

      // Use shorter intervals for responsive checking
      await new Promise(resolve => setTimeout(resolve, 250));
    }

    // Enhanced timeout error message
    const elapsedTime = Date.now() - startTime;
    const errorDetails = [
      `Timeout after ${elapsedTime}ms waiting for auth state change`,
      `Expected states: ${expectedStates.join(', ')}`,
      `Current state: ${s.authState}`,
      `Client connected: ${s.client && s.client.initialized ? 'yes' : 'no'}`,
      `Auth operation in progress: ${s.authOperationInProgress ? 'yes' : 'no'}`
    ].join(', ');

    throw new Error(errorDetails);
  }

  async function sendPhoneNumber(phoneNumber: string): Promise<void> {
    const s = globalThis.getTelegramSkillState();
    if (!s.client) throw new Error('TDLib client not initialized');

    // Check for concurrent auth operations
    if (s.authOperationInProgress) {
      throw new Error('Another authentication operation is already in progress. Please wait.');
    }

    console.log(`[telegram] Sending phone number for auth... Current auth state: ${s.authState}`);
    s.authOperationInProgress = true;
    s.config.phoneNumber = phoneNumber;
    s.config.pendingCode = true;
    state.set('config', s.config);
    publishState();

    try {
      // Send phone number and wait for TDLib to process it
      console.log('[telegram] Calling setAuthenticationPhoneNumber...');
      await setAuthenticationPhoneNumber(s.client, phoneNumber);
      console.log('[telegram] setAuthenticationPhoneNumber completed successfully');

      // Wait for auth state to change to either waitCode or an error state
      console.log('[telegram] Phone number sent, waiting for TDLib response...');
      const newState = await waitForAuthStateChange(['waitCode', 'waitPassword', 'ready'], 15000);

      console.log(`[telegram] Auth state after phone submission: ${newState}`);
    } catch (error) {
      console.error('[telegram] Error in sendPhoneNumber:', error);
      // Re-throw to be handled by the caller
      throw error;
    } finally {
      // Always clear the mutex flag
      s.authOperationInProgress = false;
      publishState();
    }
  }

  async function submitCode(code: string): Promise<void> {
    const s = globalThis.getTelegramSkillState();
    if (!s.client) throw new Error('TDLib client not initialized');

    // Check for concurrent auth operations
    if (s.authOperationInProgress) {
      throw new Error('Another authentication operation is already in progress. Please wait.');
    }

    console.log('[telegram] Submitting verification code...');
    s.authOperationInProgress = true;
    publishState();

    try {
      // Send verification code and wait for TDLib to process it
      await checkAuthenticationCode(s.client, code);

      // Wait for auth state to change to either waitPassword, ready, or remain at waitCode (if invalid)
      console.log('[telegram] Verification code sent, waiting for TDLib response...');
      const newState = await waitForAuthStateChange(['waitPassword', 'ready', 'waitCode'], 15000);

      console.log(`[telegram] Auth state after code submission: ${newState}`);

      // If still waiting for code, the submission likely failed
      if (newState === 'waitCode') {
        throw new Error('Invalid verification code. Please try again.');
      }
    } catch (error) {
      console.error('[telegram] Error in submitCode:', error);
      throw error;
    } finally {
      // Always clear the mutex flag
      s.authOperationInProgress = false;
      publishState();
    }
  }

  async function submitPassword(password: string): Promise<void> {
    const s = globalThis.getTelegramSkillState();
    if (!s.client) throw new Error('TDLib client not initialized');

    // Check for concurrent auth operations
    if (s.authOperationInProgress) {
      throw new Error('Another authentication operation is already in progress. Please wait.');
    }

    console.log('[telegram] Submitting 2FA password...');
    s.authOperationInProgress = true;
    publishState();

    try {
      // Send 2FA password and wait for TDLib to process it
      await checkAuthenticationPassword(s.client, password);

      // Wait for auth state to change to either ready or remain at waitPassword (if invalid)
      console.log('[telegram] 2FA password sent, waiting for TDLib response...');
      const newState = await waitForAuthStateChange(['ready', 'waitPassword'], 15000);

      console.log(`[telegram] Auth state after password submission: ${newState}`);

      // If still waiting for password, the submission likely failed
      if (newState === 'waitPassword') {
        throw new Error('Invalid 2FA password. Please try again.');
      }
    } catch (error) {
      console.error('[telegram] Error in submitPassword:', error);
      throw error;
    } finally {
      // Always clear the mutex flag
      s.authOperationInProgress = false;
      publishState();
    }
  }

  async function onSetupStart(): Promise<SetupStartResult> {
    const s = globalThis.getTelegramSkillState();

    // If we have a client error or stuck auth state, try database validation
    if (s.clientError || (s.authState === 'unknown' && s.client)) {
      console.log('[telegram] Checking database integrity due to error state');
      const TdLibClientClass = getTdLibClientClass();
      const tempClient = new TdLibClientClass();

      try {
        const isHealthy = await tempClient.validateDatabase();
        if (!isHealthy) {
          console.log('[telegram] Database integrity check failed, resetting auth state');
          await tempClient.resetAuthState();
          // Clear the current error state
          s.clientError = null;
          s.client = null;
          s.authState = 'unknown';
          publishState();
        }
      } catch (e) {
        console.warn('[telegram] Database validation failed:', e);
        // Continue with normal flow
      }
    }

    if (
      (!s.client && !s.clientConnecting) ||
      s.authState === 'closed' ||
      s.authState === 'unknown'
    ) {
      await initClient().catch(err => {
        const errorMsg = err instanceof Error ? err.message : String(err);
        onError({ type: 'network', message: errorMsg, source: 'initClient', recoverable: true });
      });
    }

    // If TDLib already has auth state from a previous session, start at the right step
    if (s.authState === 'waitCode') {
      return {
        step: {
          id: 'code',
          title: 'Enter Verification Code',
          description:
            'A verification code has been sent to your Telegram app or SMS. Enter it below.',
          fields: [
            {
              name: 'code',
              type: 'text',
              label: 'Verification Code',
              description: '5-digit code from Telegram',
              required: true,
            },
          ],
        },
      };
    }

    if (s.authState === 'waitPassword') {
      return {
        step: {
          id: 'password',
          title: 'Two-Factor Authentication',
          description: s.passwordHint
            ? `Enter your 2FA password. Hint: ${s.passwordHint}`
            : 'Enter your 2FA password.',
          fields: [
            {
              name: 'password',
              type: 'password',
              label: '2FA Password',
              description: 'Your Telegram 2FA password',
              required: true,
            },
          ],
        },
      };
    }

    return {
      step: {
        id: 'phone',
        title: 'Connect Telegram Account',
        description: 'Enter your phone number to connect your Telegram account.',
        fields: [
          {
            name: 'phoneNumber',
            type: 'text',
            label: 'Phone Number',
            description: 'International format (e.g., +1234567890)',
            required: true,
            placeholder: '+1234567890',
          },
        ],
      },
    };
  }

  async function onSetupSubmit(args: {
    stepId: string;
    values: Record<string, unknown>;
  }): Promise<SetupSubmitResult> {
    const s = globalThis.getTelegramSkillState();
    const { stepId, values } = args;

    console.log('[telegram] onSetupSubmit:', JSON.stringify(args));
    console.log('[telegram] Auth state:', s.authState);

    if (stepId === 'credentials') {
      const apiId = parseInt((values.apiId as string) || '', 10);
      const apiHash = ((values.apiHash as string) || '').trim();

      console.log(
        `[telegram] Setup: credentials step - apiId: ${apiId}, apiHash: ${apiHash ? '[set]' : '[empty]'}`
      );

      await initClient().catch(err => {
        const errorMsg = err instanceof Error ? err.message : String(err);
        onError({ type: 'network', message: errorMsg, source: 'initClient', recoverable: true });
      });

      return {
        status: 'next',
        nextStep: {
          id: 'phone',
          title: 'Connect Telegram Account',
          description:
            'Enter your phone number to connect your Telegram account. Please wait a moment for the connection to establish.',
          fields: [
            {
              name: 'phoneNumber',
              type: 'text',
              label: 'Phone Number',
              description: 'International format (e.g., +1234567890)',
              required: true,
              placeholder: '+1234567890',
            },
          ],
        },
      };
    }

    if (stepId === 'phone') {
      const phoneNumber = ((values.phoneNumber as string) || '').trim();

      console.log(
        `[telegram] Setup: phone step - number: ${phoneNumber ? phoneNumber.slice(0, 4) + '****' : '[empty]'}`
      );
      console.log(
        `[telegram] Setup: client connected: ${s.client !== null}, connecting: ${s.clientConnecting}, authState: ${s.authState}`
      );

      if (!phoneNumber) {
        return {
          status: 'error',
          errors: [{ field: 'phoneNumber', message: 'Phone number is required' }],
        };
      }

      if (!phoneNumber.startsWith('+')) {
        return {
          status: 'error',
          errors: [
            {
              field: 'phoneNumber',
              message: 'Phone number must start with + (international format)',
            },
          ],
        };
      }

      const phoneRegex = /^\+[1-9]\d{1,14}$/;
      const cleanPhone = phoneNumber.replace(/[\s\-()]/g, '');
      if (!phoneRegex.test(cleanPhone)) {
        return {
          status: 'error',
          errors: [
            {
              field: 'phoneNumber',
              message: 'Invalid phone number format. Use international format: +1234567890',
            },
          ],
        };
      }

      // Always check for client errors first, regardless of connection state
      if (s.clientError) {
        return {
          status: 'error',
          errors: [
            {
              field: 'phoneNumber',
              message: `Connection error: ${s.clientError}. Please try resetting the connection.`,
            },
          ],
        };
      }

      // Handle client initialization if needed
      if (!s.client) {
        if (!s.clientConnecting) {
          await initClient().catch(err => {
            const errorMsg = err instanceof Error ? err.message : String(err);
            onError({
              type: 'network',
              message: errorMsg,
              source: 'initClient',
              recoverable: true,
            });
          });
        }
        return {
          status: 'error',
          errors: [
            {
              field: 'phoneNumber',
              message: 'Connecting to Telegram... Please wait a moment and try again.',
            },
          ],
        };
      }

      // If client is connecting, wait briefly for potential errors to propagate
      if (s.clientConnecting) {
        // Give a brief moment for async errors to surface
        await new Promise(resolve => setTimeout(resolve, 500));

        // Check again for errors after waiting
        if (s.clientError) {
          return {
            status: 'error',
            errors: [
              {
                field: 'phoneNumber',
                message: `Connection error: ${s.clientError}. Please try resetting the connection.`,
              },
            ],
          };
        }

        return {
          status: 'error',
          errors: [
            {
              field: 'phoneNumber',
              message: 'Connecting to Telegram... Please wait a moment and try again.',
            },
          ],
        };
      }

      if (s.authState === 'ready') {
        console.log('[telegram] Auth state is ready');
        return { status: 'complete' };
      }

      if (s.authState === 'waitCode') {
        // Already past phone step — skip straight to code entry
        return {
          status: 'next',
          nextStep: {
            id: 'code',
            title: 'Enter Verification Code',
            description:
              'A verification code has been sent to your Telegram app or SMS. Enter it below.',
            fields: [
              {
                name: 'code',
                type: 'text' as const,
                label: 'Verification Code',
                description: '5-digit code from Telegram',
                required: true,
              },
            ],
          },
        };
      }

      if (s.authState === 'waitPassword') {
        // Already past phone + code — skip to 2FA
        return {
          status: 'next',
          nextStep: {
            id: 'password',
            title: 'Two-Factor Authentication',
            description: s.passwordHint
              ? `Enter your 2FA password. Hint: ${s.passwordHint}`
              : 'Enter your 2FA password.',
            fields: [
              {
                name: 'password',
                type: 'password' as const,
                label: '2FA Password',
                description: 'Your Telegram 2FA password',
                required: true,
              },
            ],
          },
        };
      }

      if (s.authState !== 'waitPhoneNumber') {
        console.log(`[telegram] Auth state is '${s.authState}', expected 'waitPhoneNumber'`);
        return {
          status: 'error',
          errors: [
            {
              field: 'phoneNumber',
              message: `Telegram is not ready for login (state: ${s.authState}). Please wait a moment and try again.`,
            },
          ],
        };
      }

      const cleanPhoneNumber = phoneNumber.replace(/[\s\-()]/g, '');
      console.log(`[telegram] Setup: About to call sendPhoneNumber with: ${cleanPhoneNumber.slice(0, 4)}****`);

      try {
        await sendPhoneNumber(cleanPhoneNumber);
        console.log('[telegram] Setup: sendPhoneNumber completed successfully');
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        console.error(`[telegram] Setup: sendPhoneNumber failed with error: ${errorMsg}`);

        // Smart retry logic for auth state issues
        const isDatabaseIssue = errorMsg.includes('stuck') ||
                               errorMsg.includes('timeout') ||
                               errorMsg.includes('waitPhoneNumber') ||
                               errorMsg.includes('auth state');

        if (isDatabaseIssue && s.client) {
          console.warn('[telegram] Detected possible database corruption, attempting automatic recovery');

          try {
            // Validate and potentially reset the database
            const isHealthy = await s.client.ensureDatabaseHealth();

            if (isHealthy) {
              console.log('[telegram] Database recovery successful, retrying phone submission');

              // Retry phone submission once after database recovery
              try {
                await sendPhoneNumber(cleanPhoneNumber);
                console.log('[telegram] Setup: Retry sendPhoneNumber after recovery completed successfully');

                // Continue to check final auth state below
              } catch (retryErr) {
                const retryErrorMsg = retryErr instanceof Error ? retryErr.message : String(retryErr);
                console.error(`[telegram] Setup: Retry after recovery also failed: ${retryErrorMsg}`);

                onError({
                  type: 'auth',
                  message: `Auth failed even after database recovery: ${retryErrorMsg}`,
                  source: 'setAuthenticationPhoneNumber',
                  recoverable: true,
                });

                return {
                  status: 'error',
                  errors: [
                    {
                      field: 'phoneNumber',
                      message: `Authentication failed even after automatic recovery. Please restart the app and try again.`,
                    },
                  ],
                };
              }
            } else {
              console.error('[telegram] Database recovery failed');

              onError({
                type: 'runtime',
                message: 'Database corruption detected and recovery failed',
                source: 'ensureDatabaseHealth',
                recoverable: false,
              });

              return {
                status: 'error',
                errors: [
                  {
                    field: 'phoneNumber',
                    message: `Database corruption detected. Please restart the app to reset Telegram authentication.`,
                  },
                ],
              };
            }
          } catch (healthCheckErr) {
            console.error('[telegram] Health check failed:', healthCheckErr);
          }
        } else {
          // Call onError to update the state for regular errors
          onError({
            type: 'auth',
            message: errorMsg,
            source: 'setAuthenticationPhoneNumber',
            recoverable: true,
          });

          // Return the error immediately instead of continuing
          return {
            status: 'error',
            errors: [
              {
                field: 'phoneNumber',
                message: `Failed to send phone number: ${errorMsg}. Please check your number and try again.`,
              },
            ],
          };
        }
      }

      // Check final auth state after sendPhoneNumber completed
      const updatedState = globalThis.getTelegramSkillState();
      const finalState = updatedState.authState;
      console.log(`[telegram] Final auth state after phone submission: ${finalState}`);

      if (finalState === 'waitCode') {
        return {
          status: 'next',
          nextStep: {
            id: 'code',
            title: 'Enter Verification Code',
            description:
              'A verification code has been sent to your Telegram app or SMS. Enter it below.',
            fields: [
              {
                name: 'code',
                type: 'text',
                label: 'Verification Code',
                description: '5-digit code from Telegram',
                required: true,
                placeholder: '12345',
              },
            ],
          },
        };
      }

      if (finalState === 'waitPassword') {
        return {
          status: 'next',
          nextStep: {
            id: 'password',
            title: 'Two-Factor Authentication',
            description: updatedState.passwordHint
              ? `Enter your 2FA password. Hint: ${updatedState.passwordHint}`
              : 'Enter your 2FA password.',
            fields: [
              {
                name: 'password',
                type: 'password',
                label: '2FA Password',
                description: 'Your Telegram 2FA password',
                required: true,
              },
            ],
          },
        };
      }

      if (finalState === 'ready') {
        return { status: 'complete' };
      }

      // If we get here, something unexpected happened
      return {
        status: 'error',
        errors: [
          {
            field: 'phoneNumber',
            message: `Unexpected auth state after phone submission: ${finalState}. Please try again.`,
          },
        ],
      };
    }

    if (stepId === 'code') {
      const code = ((values.code as string) || '').trim();

      console.log(`[telegram] Setup: code step - authState: ${s.authState}`);

      if (!code) {
        return {
          status: 'error',
          errors: [{ field: 'code', message: 'Verification code is required' }],
        };
      }

      try {
        await submitCode(code);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        onError({
          type: 'auth',
          message: errorMsg,
          source: 'checkAuthenticationCode',
          recoverable: true,
        });

        return {
          status: 'error',
          errors: [
            {
              field: 'code',
              message: `Failed to verify code: ${errorMsg}`,
            },
          ],
        };
      }

      // Check final auth state after submitCode completed
      const updatedState2 = globalThis.getTelegramSkillState();
      const finalState = updatedState2.authState;
      console.log(`[telegram] Final auth state after code submission: ${finalState}`);

      if (finalState === 'waitPassword') {
        return {
          status: 'next',
          nextStep: {
            id: 'password',
            title: 'Two-Factor Authentication',
            description: updatedState2.passwordHint
              ? `Enter your 2FA password. Hint: ${updatedState2.passwordHint}`
              : 'Enter your 2FA password.',
            fields: [
              {
                name: 'password',
                type: 'password',
                label: '2FA Password',
                description: 'Your Telegram 2FA password',
                required: true,
              },
            ],
          },
        };
      }

      if (finalState === 'ready') {
        return { status: 'complete' };
      }

      // If we get here, something unexpected happened
      return {
        status: 'error',
        errors: [
          {
            field: 'code',
            message: `Unexpected auth state after code submission: ${finalState}. Please try again.`,
          },
        ],
      };
    }

    if (stepId === 'password') {
      const password = ((values.password as string) || '').trim();

      console.log('[telegram] Setup: password step');

      if (!password) {
        return {
          status: 'error',
          errors: [{ field: 'password', message: '2FA password is required' }],
        };
      }

      try {
        await submitPassword(password);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        onError({
          type: 'auth',
          message: errorMsg,
          source: 'checkAuthenticationPassword',
          recoverable: true,
        });

        return {
          status: 'error',
          errors: [
            {
              field: 'password',
              message: `Failed to verify 2FA password: ${errorMsg}`,
            },
          ],
        };
      }

      // Check final auth state after submitPassword completed
      const updatedState3 = globalThis.getTelegramSkillState();
      const finalState = updatedState3.authState;
      console.log(`[telegram] Final auth state after password submission: ${finalState}`);

      if (finalState === 'ready') {
        return { status: 'complete' };
      }

      // If we get here, something unexpected happened
      return {
        status: 'error',
        errors: [
          {
            field: 'password',
            message: `Unexpected auth state after password submission: ${finalState}. Please try again.`,
          },
        ],
      };
    }

    return { status: 'error', errors: [{ field: '', message: `Unknown setup step: ${stepId}` }] };
  }

  async function onSetupCancel(): Promise<void> {
    console.log('[telegram] Setup cancelled');
    const s = globalThis.getTelegramSkillState();
    s.config.pendingCode = false;
    state.set('config', s.config);
  }

  return { onSetupStart, onSetupSubmit, onSetupCancel };
}
