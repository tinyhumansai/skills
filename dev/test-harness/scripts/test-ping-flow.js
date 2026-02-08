// Test script for server-ping skill
// Tests the new skillState pattern

console.log("=== Testing server-ping skill ===\n");

// Check that skillState is available
const skillState = globalThis.__skillState;
if (!skillState) {
  console.error("ERROR: skillState not found on globalThis.__skillState");
} else {
  console.log("✓ skillState is available on globalThis.__skillState");
  console.log("  Initial config:", JSON.stringify(skillState.config, null, 2));
  console.log("  Initial pingCount:", skillState.pingCount);
}

// Configure the skill via store (simulating setup)
state.set("config", {
  serverUrl: "https://httpbin.org/get",
  pingIntervalSec: 10,
  notifyOnDown: true,
  notifyOnRecover: true,
  verboseLogging: true,
});
console.log("\n✓ Stored config in state");

// Call init to load the config
init();
console.log("\n✓ Called init()");
console.log("  Loaded config serverUrl:", skillState.config.serverUrl);

// Mock the fetch response
__mockFetch("https://httpbin.org/get", { status: 200, body: '{"origin":"1.2.3.4"}' });
console.log("\n✓ Mocked fetch response for https://httpbin.org/get");

// Call a tool to verify tools can access skillState
console.log("\n--- Testing get-ping-stats tool ---");
try {
  const stats = callTool("get-ping-stats", {});
  console.log("✓ get-ping-stats returned:", JSON.stringify(stats, null, 2));
} catch (e) {
  console.error("✗ get-ping-stats failed:", e);
}

// Test ping-now tool (which calls doPing internally)
console.log("\n--- Testing ping-now tool ---");
try {
  const result = callTool("ping-now", {});
  console.log("✓ ping-now returned:", JSON.stringify(result, null, 2));
  console.log("  pingCount after ping:", skillState.pingCount);
} catch (e) {
  console.error("✗ ping-now failed:", e);
}

// Test update-server-url tool
console.log("\n--- Testing update-server-url tool ---");
try {
  const result = callTool("update-server-url", { url: "https://example.com/health" });
  console.log("✓ update-server-url returned:", JSON.stringify(result, null, 2));
  console.log("  New serverUrl in skillState:", skillState.config.serverUrl);
} catch (e) {
  console.error("✗ update-server-url failed:", e);
}

// Check published state
console.log("\n--- Checking published state ---");
const mockState = __getMockState();
console.log("  Published state:", JSON.stringify(mockState.state, null, 2));
console.log("  Fetch calls:", mockState.fetchCalls.length);

console.log("\n=== Test complete ===");
