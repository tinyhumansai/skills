#!/usr/bin/env node
// test-model.mjs - Run a skill test script with a real local model backend.
//
// Usage:
//   node scripts/test-model.mjs <skill-id> <script-file>
//   yarn test:model <skill-id> <script-file>
//
// Requires:
//   - Model downloaded via: yarn model:download
//   - node-llama-cpp installed: yarn install

import { existsSync, readFileSync } from 'fs';
import { dirname, join, resolve } from 'path';
import { fileURLToPath } from 'url';
import vm from 'vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = join(__dirname, '..');
const skillsDir = join(rootDir, 'skills');

const MODEL_FILENAME = 'gemma-3n-E2B-it-Q4_K_M.gguf';
const MODEL_PATH = join(rootDir, '.models', MODEL_FILENAME);

const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  dim: '\x1b[2m',
  reset: '\x1b[0m',
};

function printBanner() {
  console.log(`${colors.cyan}═══════════════════════════════════════════════════════════════${colors.reset}`);
  console.log(`${colors.cyan}          Real Model Test Runner (node-llama-cpp)              ${colors.reset}`);
  console.log(`${colors.cyan}═══════════════════════════════════════════════════════════════${colors.reset}`);
}

function printUsage() {
  console.log(`
${colors.yellow}Usage:${colors.reset}
  yarn test:model <skill-id> <script-file>

${colors.yellow}Arguments:${colors.reset}
  skill-id      The skill directory name (e.g., "example-skill")
  script-file   Path to a JavaScript test script

${colors.yellow}Prerequisites:${colors.reset}
  1. Download model: yarn model:download
  2. Install deps:   yarn install

${colors.yellow}Example:${colors.reset}
  yarn test:model example-skill dev/test-harness/scripts/test-model-usage.js
`);
}

async function main() {
  printBanner();

  const args = process.argv.slice(2);
  if (args.length < 2) {
    printUsage();
    process.exit(1);
  }

  const skillId = args[0];
  const scriptFile = args[1];

  // Check model exists
  if (!existsSync(MODEL_PATH)) {
    console.log(`\n${colors.red}Model not found at ${MODEL_PATH}${colors.reset}`);
    console.log(`${colors.yellow}Run: yarn model:download${colors.reset}`);
    process.exit(1);
  }

  // Check skill exists
  const skillDir = join(skillsDir, skillId);
  const skillIndexPath = join(skillDir, 'index.js');
  if (!existsSync(skillIndexPath)) {
    console.log(`\n${colors.red}Skill "${skillId}" not found at ${skillDir}${colors.reset}`);
    console.log(`${colors.dim}Make sure to run 'yarn build' first.${colors.reset}`);
    process.exit(1);
  }

  // Check script exists
  let resolvedScriptPath = scriptFile;
  if (!scriptFile.startsWith('/')) {
    resolvedScriptPath = resolve(rootDir, scriptFile);
  }
  if (!existsSync(resolvedScriptPath)) {
    console.log(`\n${colors.red}Script not found: ${resolvedScriptPath}${colors.reset}`);
    process.exit(1);
  }

  // Load model via ModelBridge
  console.log(`\n${colors.blue}Loading model...${colors.reset}`);
  console.log(`  ${colors.dim}${MODEL_PATH}${colors.reset}`);

  let ModelBridge;
  try {
    const bridgeModule = await import('../dev/test-harness/model-bridge.ts');
    ModelBridge = bridgeModule.ModelBridge;
  } catch {
    // Fallback: try importing compiled JS if tsx isn't being used
    try {
      const bridgeModule = await import('../dev/test-harness/model-bridge.js');
      ModelBridge = bridgeModule.ModelBridge;
    } catch (err) {
      console.error(`${colors.red}Failed to import ModelBridge: ${err.message}${colors.reset}`);
      console.error(`${colors.dim}Try running with tsx: npx tsx scripts/test-model.mjs ...${colors.reset}`);
      process.exit(1);
    }
  }

  const modelBridge = new ModelBridge();

  try {
    await modelBridge.load(MODEL_PATH);
    console.log(`${colors.green}✓ Model loaded${colors.reset}`);
  } catch (err) {
    console.error(`${colors.red}Failed to load model: ${err.message}${colors.reset}`);
    process.exit(1);
  }

  // Create mock bridge APIs (reuse pattern from test-harness.mjs)
  const mockState = {
    store: {},
    stateValues: {},
    cronSchedules: {},
    notifications: [],
    dataFiles: {},
    env: {},
    platformOs: 'macos',
  };

  const bridgeAPIs = {
    store: {
      get: key => mockState.store[key] ?? null,
      set: (key, value) => { mockState.store[key] = value; },
      delete: key => { delete mockState.store[key]; },
      keys: () => Object.keys(mockState.store),
    },
    db: {
      exec: () => {},
      get: () => null,
      all: () => [],
      kvGet: key => mockState.store[`kv:${key}`] ?? null,
      kvSet: (key, value) => { mockState.store[`kv:${key}`] = value; },
    },
    state: {
      get: key => mockState.stateValues[key],
      set: (key, value) => { mockState.stateValues[key] = value; },
      setPartial: obj => { Object.assign(mockState.stateValues, obj); },
    },
    cron: {
      register: (id, schedule) => { mockState.cronSchedules[id] = schedule; },
      unregister: id => { delete mockState.cronSchedules[id]; },
      list: () => Object.keys(mockState.cronSchedules),
    },
    platform: {
      os: () => mockState.platformOs,
      env: key => mockState.env[key] ?? '',
      notify: (title, body) => { mockState.notifications.push({ title, body }); },
    },
    net: {
      fetch: () => ({ status: 200, headers: {}, body: '{}' }),
    },
    data: {
      read: filename => mockState.dataFiles[filename] ?? null,
      write: (filename, content) => { mockState.dataFiles[filename] = content; },
    },
    skills: { list: () => [], callTool: () => null },
    // Real model bridge - this is the key difference from mock harness
    model: {
      isAvailable: () => modelBridge.isAvailable(),
      getStatus: () => modelBridge.getStatus(),
      generate: (prompt, options) => modelBridge.generate(prompt, options),
      summarize: (text, options) => modelBridge.summarize(text, options),
    },
    console: {
      log: (...args) => console.log('[skill]', ...args),
      warn: (...args) => console.warn('[skill]', ...args),
      error: (...args) => console.error('[skill]', ...args),
      info: (...args) => console.info('[skill]', ...args),
    },
  };

  // Load and run skill code
  console.log(`\n${colors.dim}Loading skill: ${skillId}${colors.reset}`);
  const skillCode = readFileSync(skillIndexPath, 'utf-8');

  const sandbox = {
    ...bridgeAPIs,
    globalThis: {},
    Buffer: globalThis.Buffer,
    Uint8Array: globalThis.Uint8Array,
    ArrayBuffer: globalThis.ArrayBuffer,
    TextEncoder: globalThis.TextEncoder,
    TextDecoder: globalThis.TextDecoder,
    setTimeout: (fn) => { return 1; },
    clearTimeout: () => {},
    setInterval: (fn) => { return 1; },
    clearInterval: () => {},
    Date, JSON, Object, Array, String, Number, Boolean, Math,
    Error, TypeError, ReferenceError, Map, Set, WeakMap, WeakSet,
    Promise, RegExp, Symbol, BigInt,
    parseInt, parseFloat, isNaN, isFinite,
    encodeURIComponent, decodeURIComponent,
    btoa: str => Buffer.from(str, 'binary').toString('base64'),
    atob: str => Buffer.from(str, 'base64').toString('binary'),
    navigator: { userAgent: 'ModelTestHarness' },
    location: { protocol: 'https:', hostname: 'localhost', port: '', href: 'https://localhost/' },
    tools: [],
    init: undefined,
    start: undefined,
    stop: undefined,
    onCronTrigger: undefined,
    onSessionStart: undefined,
    onSessionEnd: undefined,
    onSetupStart: undefined,
    onSetupSubmit: undefined,
    onSetupCancel: undefined,
    onDisconnect: undefined,
    onListOptions: undefined,
    onSetOption: undefined,
  };

  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;

  const context = vm.createContext(sandbox);

  try {
    vm.runInContext(skillCode, context, { filename: skillIndexPath, timeout: 30000 });
    console.log(`${colors.green}✓ Skill code loaded${colors.reset}`);
  } catch (err) {
    console.error(`${colors.red}Skill eval error: ${err.message}${colors.reset}`);
    await modelBridge.dispose();
    process.exit(1);
  }

  // Call init/start if available
  if (typeof sandbox.globalThis.init === 'function') {
    try {
      sandbox.globalThis.init();
      console.log(`${colors.green}✓ init()${colors.reset}`);
    } catch (err) {
      console.warn(`${colors.yellow}init() error: ${err.message}${colors.reset}`);
    }
  }

  if (typeof sandbox.globalThis.start === 'function') {
    try {
      sandbox.globalThis.start();
      console.log(`${colors.green}✓ start()${colors.reset}`);
    } catch (err) {
      console.warn(`${colors.yellow}start() error: ${err.message}${colors.reset}`);
    }
  }

  // Run test script
  console.log(`\n${colors.yellow}═══════════════════════════════════════════════════════════════${colors.reset}`);
  console.log(`${colors.yellow}                    Running Test Script                        ${colors.reset}`);
  console.log(`${colors.yellow}═══════════════════════════════════════════════════════════════${colors.reset}`);
  console.log(`${colors.dim}Script: ${resolvedScriptPath}${colors.reset}\n`);

  const scriptCode = readFileSync(resolvedScriptPath, 'utf-8');

  try {
    vm.runInContext(scriptCode, context, { filename: resolvedScriptPath, timeout: 600000 }); // 10 min timeout for model
    console.log(`\n${colors.green}═══════════════════════════════════════════════════════════════${colors.reset}`);
    console.log(`${colors.green}                    Script Completed                           ${colors.reset}`);
    console.log(`${colors.green}═══════════════════════════════════════════════════════════════${colors.reset}`);
  } catch (err) {
    console.error(`\n${colors.red}Script error: ${err.message}${colors.reset}`);
    if (err.stack) console.error(colors.dim + err.stack.split('\n').slice(0, 5).join('\n') + colors.reset);
  }

  // Cleanup
  await modelBridge.dispose();
  console.log(`${colors.dim}Model resources released.${colors.reset}`);
}

main().catch(err => {
  console.error(`Fatal: ${err.message}`);
  process.exit(1);
});
