// test-model-usage.js - Example test script for the real model bridge.
//
// Run with:
//   yarn test:model example-skill dev/test-harness/scripts/test-model-usage.js

console.log("=== Model Bridge Test ===");

// Check availability
var available = model.isAvailable();
console.log("Model available:", available);

if (!available) {
  console.log("Model not loaded. Run: yarn model:download");
} else {
  // Check status
  var status = model.getStatus();
  console.log("Model status:", JSON.stringify(status, null, 2));

  // Test generate
  console.log("\n--- Generate Test ---");
  var result = model.generate("What is Bitcoin in one sentence?", { maxTokens: 100 });
  console.log("Generated:", result);

  // Test summarize
  console.log("\n--- Summarize Test ---");
  var text = "Bitcoin is a decentralized digital currency, without a central bank or single administrator, that can be sent from user to user on the peer-to-peer bitcoin network without the need for intermediaries. Transactions are verified by network nodes through cryptography and recorded in a public distributed ledger called a blockchain.";
  var summary = model.summarize(text, { maxTokens: 50 });
  console.log("Summary:", summary);

  // Test generate with custom options
  console.log("\n--- Generate with Options ---");
  var creative = model.generate("Write a haiku about Ethereum.", {
    maxTokens: 50,
    temperature: 0.9,
    topP: 0.95,
  });
  console.log("Creative:", creative);
}

console.log("\n=== Done ===");
