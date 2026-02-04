/**
 * test-ping-flow.js - Example test script for server-ping skill
 *
 * Tests the main ping flow including successful pings, failures,
 * and recovery notifications.
 *
 * Run with:
 *   yarn test:script server-ping scripts/examples/test-ping-flow.js
 */

console.log('=== Testing server-ping flow ===\n');

// Configure the skill via store (simulating setup completion)
store.set('config', {
  serverUrl: 'https://api.example.com/health',
  pingIntervalSec: 10,
  notifyOnDown: true,
  notifyOnRecover: true,
  verboseLogging: true,
});

// Re-initialize with the new config
console.log('Re-initializing with config...');
init();

// Mock successful ping response
__mockFetch('https://api.example.com/health', {
  status: 200,
  body: JSON.stringify({ status: 'ok', timestamp: Date.now() }),
});

// Start the skill
console.log('Starting skill...');
start();

// Check available tools
console.log('\nAvailable tools:', listTools());

// Get initial stats
let stats = callTool('get-ping-stats', {});
console.log('\nInitial stats:', JSON.stringify(stats, null, 2));

// Check published state
let publishedState = __getMockState().state;
console.log('\nPublished state:', JSON.stringify(publishedState, null, 2));

// Simulate a few more successful pings by triggering the interval
console.log('\n--- Triggering 2 more pings (success) ---');
const timers = listTimers();
console.log('Active timers:', timers);

if (timers.length > 0) {
  // Trigger the ping timer twice
  for (let i = 0; i < 2; i++) {
    triggerTimer(timers[0].id);
  }
}

// Check stats after pings
stats = callTool('get-ping-stats', {});
console.log('\nStats after successful pings:', JSON.stringify(stats, null, 2));

// Now simulate a failure
console.log('\n--- Simulating server failure ---');
__mockFetchError('https://api.example.com/health', 'Connection refused');

if (timers.length > 0) {
  triggerTimer(timers[0].id);
}

// Check notifications
const mockState = __getMockState();
console.log('\nNotifications:', mockState.notifications);

// Check updated stats
stats = callTool('get-ping-stats', {});
console.log('Stats after failure:', JSON.stringify(stats, null, 2));

// Simulate recovery
console.log('\n--- Simulating server recovery ---');
__mockFetch('https://api.example.com/health', {
  status: 200,
  body: JSON.stringify({ status: 'ok' }),
});

if (timers.length > 0) {
  triggerTimer(timers[0].id);
}

// Check notifications (should have recovery notification now)
console.log('\nAll notifications:', __getMockState().notifications);

// Check final stats
stats = callTool('get-ping-stats', {});
console.log('\nFinal stats:', JSON.stringify(stats, null, 2));

// Check ping history
const history = callTool('get-ping-history', { limit: 5 });
console.log('\nRecent ping history:', JSON.stringify(history, null, 2));

// Check data files written
console.log('\nData files written:', Object.keys(__getMockState().dataFiles));

// Read the ping log file
const pingLog = data.read('ping-log.txt');
if (pingLog) {
  console.log('\nPing log file contents:');
  console.log(pingLog);
}

console.log('\n=== Test completed successfully ===');
