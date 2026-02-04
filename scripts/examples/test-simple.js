/**
 * test-simple.js - Minimal test script to debug the harness
 */

console.log('=== Simple test ===');

console.log('typeof tools:', typeof tools);
console.log('tools:', tools);

if (tools && tools.length) {
  console.log('tools.length:', tools.length);
  console.log('First tool:', tools[0]);
}

console.log('\nTrying listTools()...');
var toolNames = listTools();
console.log('Tool names:', toolNames);

console.log('\n=== Done ===');
