/**
 * test-telegram-flow.ts - Live Telegram connection test
 *
 * Tests the basic Telegram connection flow including:
 * 1. Creating a TelegramClient with API credentials
 * 2. Connecting to Telegram servers
 * 3. Calling help.GetAppConfig (no auth required)
 * 4. Optionally checking authentication status
 *
 * Run with:
 *   TELEGRAM_API_ID=xxx TELEGRAM_API_HASH=xxx deno run --allow-all scripts/examples/test-telegram-flow.ts
 *
 * Or via yarn:
 *   TELEGRAM_API_ID=xxx TELEGRAM_API_HASH=xxx yarn test:live telegram scripts/examples/test-telegram-flow.ts
 */

// Import gramjs using Deno's npm compatibility
import { TelegramClient } from 'npm:telegram@2.26.22';
import { StringSession } from 'npm:telegram@2.26.22/sessions/index.js';
import { Api } from 'npm:telegram@2.26.22/tl/index.js';

// Colors for console output
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
  reset: '\x1b[0m',
  dim: '\x1b[2m',
};

function log(message: string, color = colors.reset): void {
  console.log(`${color}${message}${colors.reset}`);
}

function logStep(step: string): void {
  log(`\n▶ ${step}`, colors.cyan);
}

function logSuccess(message: string): void {
  log(`  ✓ ${message}`, colors.green);
}

function logError(message: string): void {
  log(`  ✗ ${message}`, colors.red);
}

function logInfo(message: string): void {
  log(`  ℹ ${message}`, colors.dim);
}

async function main(): Promise<void> {
  log('=== Telegram Live Connection Test ===\n', colors.magenta);

  // Step 1: Get credentials from environment
  logStep('Step 1: Loading credentials');

  const apiId = Deno.env.get('TELEGRAM_API_ID');
  const apiHash = Deno.env.get('TELEGRAM_API_HASH');
  const sessionString = Deno.env.get('TELEGRAM_SESSION') || '';

  if (!apiId || !apiHash) {
    logError('Missing TELEGRAM_API_ID or TELEGRAM_API_HASH environment variables');
    log('\nSet them like this:', colors.yellow);
    log('  export TELEGRAM_API_ID=your_api_id');
    log('  export TELEGRAM_API_HASH=your_api_hash');
    log('\nGet credentials from: https://my.telegram.org', colors.dim);
    Deno.exit(1);
  }

  logSuccess(`API ID: ${apiId}`);
  logSuccess(`API Hash: ${apiHash.substring(0, 4)}...${apiHash.substring(apiHash.length - 4)}`);
  if (sessionString) {
    logSuccess(`Session: ${sessionString.substring(0, 10)}... (${sessionString.length} chars)`);
  } else {
    logInfo('No session string provided (unauthenticated test only)');
  }

  // Step 2: Create TelegramClient
  logStep('Step 2: Creating TelegramClient');

  const session = new StringSession(sessionString);
  const client = new TelegramClient(session, parseInt(apiId), apiHash, {
    connectionRetries: 5,
    useWSS: true, // Use WebSocket Secure
  });

  logSuccess('TelegramClient created');

  // Step 3: Connect to Telegram
  logStep('Step 3: Connecting to Telegram servers');

  try {
    await client.connect();
    logSuccess('Connected to Telegram!');
  } catch (error) {
    logError(`Connection failed: ${error}`);
    Deno.exit(1);
  }

  // Step 4: Call help.GetAppConfig
  logStep('Step 4: Calling help.GetAppConfig');

  try {
    const appConfig = await client.invoke(
      new Api.help.GetAppConfig({ hash: 0 })
    );

    logSuccess('GetAppConfig succeeded!');

    // The result can be either AppConfig or AppConfigNotModified
    if (appConfig.className === 'AppConfigNotModified') {
      logInfo('Result: AppConfigNotModified (config unchanged)');
    } else {
      logInfo(`Result type: ${appConfig.className || 'AppConfig'}`);

      // Try to extract some config values
      // deno-lint-ignore no-explicit-any
      const config = appConfig as any;
      if (config.config) {
        // It's wrapped in a config property
        logInfo(`Config hash: ${config.hash || 'N/A'}`);

        // Show a few sample config keys if available
        const configObj = config.config;
        if (typeof configObj === 'object') {
          const keys = Object.keys(configObj).slice(0, 5);
          if (keys.length > 0) {
            logInfo(`Sample config keys: ${keys.join(', ')}...`);
          }
        }
      } else if (config.hash !== undefined) {
        logInfo(`Config hash: ${config.hash}`);
      }
    }

    // Show full result structure
    log('\n  Full result structure:', colors.dim);
    console.log(JSON.stringify({
      className: appConfig.className,
      // deno-lint-ignore no-explicit-any
      hasConfig: 'config' in (appConfig as any),
      // deno-lint-ignore no-explicit-any
      hash: (appConfig as any).hash,
    }, null, 2));

  } catch (error) {
    logError(`GetAppConfig failed: ${error}`);
    // Continue to check other things
  }

  // Step 5: Check authorization status
  logStep('Step 5: Checking authorization status');

  try {
    const isAuthorized = await client.checkAuthorization();
    if (isAuthorized) {
      logSuccess('Client is AUTHORIZED');

      // Try to get user info
      try {
        const me = await client.getMe();
        if (me) {
          logInfo(`Logged in as: ${me.firstName || ''} ${me.lastName || ''} (@${me.username || 'no username'})`);
          logInfo(`User ID: ${me.id}`);
          logInfo(`Phone: ${me.phone || 'N/A'}`);
          logInfo(`Premium: ${me.premium ? 'Yes' : 'No'}`);
        }
      } catch (meError) {
        logInfo(`Could not get user info: ${meError}`);
      }
    } else {
      logInfo('Client is NOT authorized (need to sign in)');
      logInfo('To authenticate, you would need to:');
      logInfo('  1. Call client.sendCode() with your phone number');
      logInfo('  2. Enter the code you receive');
      logInfo('  3. Call client.signIn() with the code');
    }
  } catch (authError) {
    logError(`Authorization check failed: ${authError}`);
  }

  // Step 6: Test another simple API call (getNearestDc)
  logStep('Step 6: Calling help.GetNearestDc');

  try {
    const nearestDc = await client.invoke(new Api.help.GetNearestDc());
    logSuccess('GetNearestDc succeeded!');
    // deno-lint-ignore no-explicit-any
    const dc = nearestDc as any;
    logInfo(`Country: ${dc.country || 'Unknown'}`);
    logInfo(`This DC: ${dc.thisDc || 'Unknown'}`);
    logInfo(`Nearest DC: ${dc.nearestDc || 'Unknown'}`);
  } catch (error) {
    logError(`GetNearestDc failed: ${error}`);
  }

  // Step 7: Save session if authenticated
  if (sessionString === '' && await client.checkAuthorization()) {
    logStep('Step 7: Saving session');
    const newSession = client.session.save() as unknown as string;
    if (newSession) {
      logSuccess('Session saved! Set this env var for future tests:');
      log(`\n  export TELEGRAM_SESSION="${newSession}"`, colors.yellow);
    }
  }

  // Clean up
  logStep('Cleanup: Disconnecting');

  try {
    await client.disconnect();
    logSuccess('Disconnected cleanly');
  } catch (error) {
    logInfo(`Disconnect note: ${error}`);
  }

  log('\n=== Test Complete ===\n', colors.magenta);
}

// Run the main function
main().catch((error) => {
  console.error('Fatal error:', error);
  Deno.exit(1);
});
