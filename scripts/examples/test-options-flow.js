/**
 * test-options-flow.js - Example test script for runtime options
 *
 * Tests the options system for changing skill behavior at runtime.
 *
 * Run with:
 *   yarn test:script server-ping scripts/examples/test-options-flow.js
 */

console.log('=== Testing options flow ===\n');

// Set up initial config
store.set('config', {
  serverUrl: 'https://api.example.com/health',
  pingIntervalSec: 10,
  notifyOnDown: true,
  notifyOnRecover: true,
  verboseLogging: false,
});

// Initialize and start
init();
__mockFetch('https://api.example.com/health', {
  status: 200,
  body: '{"ok":true}',
});
start();

// Check available options
console.log('--- Listing available options ---');
const optionsResult = onListOptions();
console.log('Available options:');
for (const opt of optionsResult.options) {
  console.log(`  - ${opt.name}: ${JSON.stringify(opt.value)} (${opt.type})`);
  if (opt.options) {
    console.log(`    choices: ${opt.options.map((o) => o.label).join(', ')}`);
  }
}

// Change ping interval
console.log('\n--- Changing ping interval to 30s ---');
onSetOption({ name: 'pingIntervalSec', value: '30' });

// Verify the change
const config = store.get('config');
console.log('Updated config.pingIntervalSec:', config.pingIntervalSec);

// Check timers were updated
const timers = listTimers();
console.log('Active timers after change:', timers);

// Change notification settings
console.log('\n--- Disabling notifications ---');
onSetOption({ name: 'notifyOnDown', value: false });
onSetOption({ name: 'notifyOnRecover', value: false });

// Verify
const config2 = store.get('config');
console.log('Updated notification settings:', {
  notifyOnDown: config2.notifyOnDown,
  notifyOnRecover: config2.notifyOnRecover,
});

// Enable verbose logging
console.log('\n--- Enabling verbose logging ---');
onSetOption({ name: 'verboseLogging', value: true });

// Trigger a ping to see verbose output
console.log('\n--- Triggering ping with verbose logging ---');
if (timers.length > 0) {
  triggerTimer(timers[0].id);
}

// List options again to see updated values
console.log('\n--- Final option values ---');
const finalOptions = onListOptions();
for (const opt of finalOptions.options) {
  console.log(`  ${opt.name}: ${JSON.stringify(opt.value)}`);
}

console.log('\n=== Options flow test completed ===');
