/**
 * test-debug.js - Debug tools access
 */

console.log('=== Debug test ===');

// Check __skill directly
console.log('typeof __skill:', typeof __skill);
console.log('__skill:', __skill);

if (__skill && __skill.default) {
  console.log('__skill.default:', __skill.default);
  console.log('__skill.default.tools:', __skill.default.tools);

  if (__skill.default.tools) {
    console.log('Tools count:', __skill.default.tools.length);
    for (var i = 0; i < __skill.default.tools.length; i++) {
      var t = __skill.default.tools[i];
      console.log('Tool ' + i + ':', typeof t, t ? t.name : 'undefined');
    }
  }
}

console.log('\nNow checking global tools:');
console.log('typeof tools:', typeof tools);
console.log('Array.isArray(tools):', Array.isArray(tools));
console.log('tools:', tools);

console.log('\n=== Done ===');
