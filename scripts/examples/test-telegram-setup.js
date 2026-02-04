/**
 * test-telegram-setup.js - Test the Telegram skill setup flow (mocked)
 *
 * Environment variables (TELEGRAM_API_ID, TELEGRAM_API_HASH) are automatically
 * loaded from .env file via the --env flag and forwarded to the mock harness.
 *
 * This tests the setup wizard logic:
 * - Validation of credentials and phone number
 * - State persistence to store
 * - Request queue for async operations
 *
 * Run with:
 *   yarn test:script telegram scripts/examples/test-telegram-setup.js
 */

console.log('=== Telegram Setup Flow Test (Mocked) ===\n');

// Helper to pretty-print objects
function pp(obj) {
  console.log(JSON.stringify(obj, null, 2));
}

// Helper to simulate delay (not actual delay in mocked runner)
function log(msg) {
  console.log(`[test] ${msg}`);
}



// ---------------------------------------------------------------------------
// Test 1: Test setup flow - onSetupStart
// ---------------------------------------------------------------------------
log('\nTest 1: Testing onSetupStart...');

// init();
console.log('init done');

const setupStartResult = triggerSetupStart();
log('Setup start result:');
pp(setupStartResult);

// Should return credentials step (no env vars set in mock)
if (!setupStartResult.step) {
  throw new Error('onSetupStart should return a step');
}

const firstStepId = setupStartResult.step.id;
log(`First step: ${firstStepId}`);

triggerSetupSubmit(firstStepId, { phoneNumber: '+96569028879' });
