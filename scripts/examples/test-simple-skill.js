/**
 * test-simple-skill.js - Test the simple skill harness
 */

console.log("=== Testing simple-skill ===\n");

// Test tools
console.log("Available tools:", listTools());

// Call greet tool
var result = callTool("greet", { name: "Claude" });
console.log("Greet result:", result);

// Call again to increment count
result = callTool("greet", { name: "User" });
console.log("Second greet:", result);

// Get count
result = callTool("get-count", {});
console.log("Count:", result);

// Test setup flow
console.log("\n--- Setup Flow ---");
var step = triggerSetupStart();
console.log("Setup step:", JSON.stringify(step, null, 2));

var submitResult = triggerSetupSubmit("greeting", { greeting: "Howdy" });
console.log("Submit result:", submitResult);

// Verify config was saved
var savedConfig = store.get("config");
console.log("Saved config:", savedConfig);

// Greet again with new greeting
result = callTool("greet", { name: "Partner" });
console.log("Greet with new greeting:", result);

console.log("\n=== Test completed ===");
