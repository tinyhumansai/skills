/**
 * test-setup-flow.js - Example test script for server-ping setup wizard
 *
 * Tests the multi-step setup flow including validation and config persistence.
 *
 * Run with:
 *   yarn test:script server-ping scripts/examples/test-setup-flow.js
 */

console.log('=== Testing setup flow ===\n');

// Start the setup wizard
console.log('--- Step 1: Start Setup ---');
const step1 = triggerSetupStart();
console.log('Setup step 1:', JSON.stringify(step1, null, 2));

// Test validation - empty URL should fail
console.log('\n--- Testing validation (empty URL) ---');
let result = triggerSetupSubmit('server-config', {
  serverUrl: '',
  pingIntervalSec: '10',
});
console.log('Result (should be error):', JSON.stringify(result, null, 2));

// Test validation - invalid URL should fail
console.log('\n--- Testing validation (invalid URL) ---');
result = triggerSetupSubmit('server-config', {
  serverUrl: 'not-a-url',
  pingIntervalSec: '10',
});
console.log('Result (should be error):', JSON.stringify(result, null, 2));

// Submit valid server config
console.log('\n--- Step 1: Submit valid config ---');
result = triggerSetupSubmit('server-config', {
  serverUrl: 'https://my-server.com/api/health',
  pingIntervalSec: '30',
});
console.log('Result:', JSON.stringify(result, null, 2));

// Should get step 2 (notification preferences)
if (result.status === 'next' && result.nextStep) {
  console.log('\n--- Step 2: Notification Preferences ---');
  console.log('Fields:', result.nextStep.fields.map((f) => f.name));

  // Submit notification preferences
  result = triggerSetupSubmit('notification-config', {
    notifyOnDown: true,
    notifyOnRecover: false,
  });
  console.log('Final result:', JSON.stringify(result, null, 2));
}

// Verify config was persisted
console.log('\n--- Verifying persisted config ---');
const savedConfig = store.get('config');
console.log('Saved config:', JSON.stringify(savedConfig, null, 2));

// Check data file was written
const configFile = data.read('config.json');
console.log('\nConfig file contents:', configFile);

// Now test that the skill can start with the saved config
console.log('\n--- Testing skill start with saved config ---');
init(); // Re-read config from store

// Mock the server
__mockFetch('https://my-server.com/api/health', {
  status: 200,
  body: '{"status":"healthy"}',
});

start();

// Verify it's working
const stats = callTool('get-ping-stats', {});
console.log('Stats after start:', JSON.stringify(stats, null, 2));

console.log('\n=== Setup flow test completed ===');
