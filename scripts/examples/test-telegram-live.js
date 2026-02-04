/**
 * test-telegram-live.js - Live Telegram connection test
 *
 * Tests the basic Telegram connection flow including:
 * 1. Creating a TelegramClient with API credentials
 * 2. Connecting to Telegram servers
 * 3. Calling help.GetAppConfig (no auth required)
 * 4. Checking authorization status
 *
 * Run with:
 *   TELEGRAM_API_ID=xxx TELEGRAM_API_HASH=xxx deno run --allow-all scripts/examples/test-telegram-live.js
 *
 * Or via yarn:
 *   TELEGRAM_API_ID=xxx TELEGRAM_API_HASH=xxx yarn test:live scripts/examples/test-telegram-live.js
 *
 * Environment Variables:
 *   TELEGRAM_API_ID     - Your Telegram API ID from my.telegram.org (required)
 *   TELEGRAM_API_HASH   - Your Telegram API Hash (required)
 *   TELEGRAM_SESSION    - Saved session string for authenticated calls (optional)
 */

// Using dynamic import for ESM compatibility
const { TelegramClient } = await import('npm:telegram@2.26.22');
const { StringSession } = await import('npm:telegram@2.26.22/sessions/index.js');
const { Api } = await import('npm:telegram@2.26.22/tl/index.js');

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

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function logStep(step) {
  log(`\n▶ ${step}`, colors.cyan);
}

function logSuccess(message) {
  log(`  ✓ ${message}`, colors.green);
}

function logError(message) {
  log(`  ✗ ${message}`, colors.red);
}

function logInfo(message) {
  log(`  ℹ ${message}`, colors.dim);
}

// Get environment variable (works in Deno)
function getEnv(key) {
  // Deno environment
  if (typeof Deno !== 'undefined') {
    return Deno.env.get(key) || '';
  }
  // Node.js fallback
  if (typeof process !== 'undefined' && process.env) {
    return process.env[key] || '';
  }
  return '';
}

async function main() {
  log('=== Telegram Live Connection Test ===\n', colors.magenta);

  // Step 1: Get credentials from environment
  logStep('Step 1: Loading credentials');

  const apiId = getEnv('TELEGRAM_API_ID');
  const apiHash = getEnv('TELEGRAM_API_HASH');
  const sessionString = getEnv('TELEGRAM_SESSION') || '';

  if (!apiId || !apiHash) {
    logError('Missing TELEGRAM_API_ID or TELEGRAM_API_HASH environment variables');
    log('\nSet them like this:', colors.yellow);
    log('  export TELEGRAM_API_ID=your_api_id');
    log('  export TELEGRAM_API_HASH=your_api_hash');
    log('\nGet credentials from: https://my.telegram.org', colors.dim);
    if (typeof Deno !== 'undefined') {
      Deno.exit(1);
    } else {
      process.exit(1);
    }
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
    if (typeof Deno !== 'undefined') {
      Deno.exit(1);
    } else {
      process.exit(1);
    }
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
      if (appConfig.config) {
        logInfo(`Config hash: ${appConfig.hash || 'N/A'}`);

        // Show a few sample config keys if available
        const configObj = appConfig.config;
        if (typeof configObj === 'object') {
          const keys = Object.keys(configObj).slice(0, 5);
          if (keys.length > 0) {
            logInfo(`Sample config keys: ${keys.join(', ')}...`);
          }
        }
      } else if (appConfig.hash !== undefined) {
        logInfo(`Config hash: ${appConfig.hash}`);
      }
    }

    // Show full result structure
    log('\n  Full result structure:', colors.dim);
    console.log(JSON.stringify({
      className: appConfig.className,
      hasConfig: 'config' in appConfig,
      hash: appConfig.hash,
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
    logInfo(`Country: ${nearestDc.country || 'Unknown'}`);
    logInfo(`This DC: ${nearestDc.thisDc || 'Unknown'}`);
    logInfo(`Nearest DC: ${nearestDc.nearestDc || 'Unknown'}`);
  } catch (error) {
    logError(`GetNearestDc failed: ${error}`);
  }

  // Step 7: Save session if authenticated
  if (sessionString === '' && await client.checkAuthorization()) {
    logStep('Step 7: Saving session');
    const newSession = client.session.save();
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
  if (typeof Deno !== 'undefined') {
    Deno.exit(1);
  } else {
    process.exit(1);
  }
});
