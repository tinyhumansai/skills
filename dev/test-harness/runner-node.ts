#!/usr/bin/env tsx
/**
 * runner-node.ts - QuickJS Skill Script Runner (Node.js)
 *
 * Loads a compiled skill from skills/<skill-id>/index.js and executes
 * a user-written test script against it. Provides the same bridge APIs
 * as the Rust QuickJS runtime.
 *
 * Usage:
 *   npx tsx dev/test-harness/runner-node.ts <skill-id> <script-file>
 *   yarn test:script <skill-id> <script-file>
 *
 * Example:
 *   yarn test:script simple-skill scripts/examples/test-simple-skill.js
 *
 * Supported Features:
 *   - Bridge APIs: db, store, net, platform, state, data, cron, skills
 *   - Lifecycle hooks: init, start, stop
 *   - Setup flow: onSetupStart, onSetupSubmit
 *   - Options: onListOptions, onSetOption
 *   - Session events: onSessionStart, onSessionEnd
 *   - Timer mocking: setTimeout, setInterval
 *
 * Limitations:
 *   - Tools that reference IIFE-scoped state variables (like PING_COUNT, FAIL_COUNT)
 *     may throw ReferenceError because the new Function() sandbox doesn't expose
 *     globalThis properties as variable bindings. The production Rust QuickJS runtime
 *     handles this correctly.
 *   - Use simple-skill as a reference for harness-compatible skill structure.
 */

import { existsSync, readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createBridgeAPIs } from './bootstrap-node';
import {
  getMockState,
  initMockState,
  mockFetchError,
  mockFetchResponse,
  resetMockState,
  setEnv,
  setPlatformOs,
} from './mock-state';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Colors for terminal output
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  reset: '\x1b[0m',
  dim: '\x1b[2m',
};

function printBanner(): void {
  console.log(`${colors.cyan}═══════════════════════════════════════════════════════════════${colors.reset}`);
  console.log(`${colors.cyan}            QuickJS Skill Script Runner (Node.js)              ${colors.reset}`);
  console.log(`${colors.cyan}═══════════════════════════════════════════════════════════════${colors.reset}`);
}

function printUsage(): void {
  console.log(`
${colors.yellow}Usage:${colors.reset}
  npx tsx dev/test-harness/runner-node.ts <skill-id> <script-file> [options]

${colors.yellow}Arguments:${colors.reset}
  skill-id      The skill directory name (e.g., "server-ping")
  script-file   Path to a JavaScript test script

${colors.yellow}Options:${colors.reset}
  --wait=<ms>   Wait specified milliseconds before cleanup (for async connections)

${colors.yellow}Examples:${colors.reset}
  npx tsx dev/test-harness/runner-node.ts server-ping scripts/examples/test-ping-flow.js
  yarn test:script server-ping scripts/examples/test-ping-flow.js
  yarn test:script telegram scripts/examples/test-telegram-setup.js --wait=10000

${colors.yellow}Script Helpers Available:${colors.reset}
  callTool(name, args)           - Call a skill tool, returns parsed result
  triggerCron(scheduleId)        - Manually trigger onCronTrigger
  triggerSetupStart()            - Call onSetupStart, returns step definition
  triggerSetupSubmit(stepId, values) - Call onSetupSubmit
  triggerTimer(timerId)          - Fire a specific timer callback
  __mockFetch(url, response)     - Set up mock HTTP response
  __mockFetchError(url, message) - Set up mock HTTP error
  __getMockState()               - Get full mock state for inspection
  __resetMockState()             - Reset all mocks to initial state
  __setEnv(key, value)           - Set environment variable
  __setPlatformOs(os)            - Set platform.os() return value
`);
}

async function main(): Promise<void> {
  printBanner();

  const args = process.argv.slice(2);
  if (args.length < 2) {
    printUsage();
    process.exit(1);
  }

  // Parse --wait flag for async connection waiting
  let waitMs = 0;
  const filteredArgs: string[] = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--wait' && args[i + 1]) {
      waitMs = parseInt(args[i + 1], 10);
      i++; // Skip the value
    } else if (args[i].startsWith('--wait=')) {
      waitMs = parseInt(args[i].split('=')[1], 10);
    } else {
      filteredArgs.push(args[i]);
    }
  }

  if (filteredArgs.length < 2) {
    printUsage();
    process.exit(1);
  }

  const skillId = filteredArgs[0];
  const scriptFile = filteredArgs[1];

  // Resolve paths relative to the skills repo root
  const rootDir = resolve(__dirname, '../..');
  const skillDir = resolve(rootDir, 'skills', skillId);
  const skillIndexPath = resolve(skillDir, 'index.js');
  const skillManifestPath = resolve(skillDir, 'manifest.json');

  // Check if skill exists
  if (!existsSync(skillIndexPath)) {
    console.error(`${colors.red}Error: Skill "${skillId}" not found at ${skillDir}${colors.reset}`);
    console.error(`${colors.dim}Make sure to run 'yarn build' first.${colors.reset}`);
    process.exit(1);
  }

  // Check if script exists
  let resolvedScriptPath = scriptFile;
  if (!scriptFile.startsWith('/')) {
    resolvedScriptPath = resolve(rootDir, scriptFile);
  }

  if (!existsSync(resolvedScriptPath)) {
    console.error(`${colors.red}Error: Script file not found: ${resolvedScriptPath}${colors.reset}`);
    process.exit(1);
  }

  // Load manifest
  let manifest: { id: string; name: string; version: string };
  try {
    const manifestText = readFileSync(skillManifestPath, 'utf-8');
    manifest = JSON.parse(manifestText);
    console.log(`\n${colors.blue}Loaded skill: ${manifest.name} v${manifest.version} (${manifest.id})${colors.reset}`);
  } catch (e) {
    console.error(`${colors.red}Error loading manifest: ${e}${colors.reset}`);
    process.exit(1);
  }

  // Initialize mock state
  initMockState();

  // Forward environment variables to mock state
  const envVarsToForward = [
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_PHONE_NUMBER',
    'NOTION_API_KEY',
    'OPENAI_API_KEY',
  ];
  for (const key of envVarsToForward) {
    const value = process.env[key];
    if (value) {
      setEnv(key, value);
    }
  }

  // Create bridge APIs
  const bridgeAPIs = await createBridgeAPIs();

  // Build the global context that will be shared by skill and test script
  const G: Record<string, unknown> = {
    ...bridgeAPIs,
  };

  // Make globalThis/self/window point to G (the shared global)
  G.globalThis = G;
  G.self = G;
  G.window = G;

  // Add __helpers for mock state access
  G.__helpers = {
    getMockState,
    mockFetchResponse,
    mockFetchError,
    resetMockState,
    setEnv,
    setPlatformOs,
  };

  // IMPORTANT: Set WebSocket on globalThis BEFORE loading skill code
  if (bridgeAPIs.WebSocket) {
    // @ts-ignore - setting global WebSocket
    globalThis.WebSocket = bridgeAPIs.WebSocket;
    // @ts-ignore
    globalThis.window = globalThis;
  }

  // Load the skill code
  console.log(`${colors.dim}Loading skill code...${colors.reset}`);
  const skillCode = readFileSync(skillIndexPath, 'utf-8');

  // Run code with access to shared global G
  const runInContext = (code: string) => {
    const fn = new Function('G', `
      "use strict";
      // Destructure globals from G
      var console = G.console;
      var store = G.store;
      var db = G.db;
      var net = G.net;
      var platform = G.platform;
      var state = G.state;
      var data = G.data;
      var cron = G.cron;
      var skills = G.skills;
      var setTimeout = G.setTimeout;
      var setInterval = G.setInterval;
      var clearTimeout = G.clearTimeout;
      var clearInterval = G.clearInterval;
      var Date = G.Date;
      var JSON = G.JSON;
      var Object = G.Object;
      var Array = G.Array;
      var String = G.String;
      var Number = G.Number;
      var Boolean = G.Boolean;
      var Math = G.Math;
      var Error = G.Error;
      var TypeError = G.TypeError;
      var ReferenceError = G.ReferenceError;
      var Map = G.Map;
      var Set = G.Set;
      var WeakMap = G.WeakMap;
      var WeakSet = G.WeakSet;
      var Promise = G.Promise;
      var RegExp = G.RegExp;
      var Symbol = G.Symbol;
      var BigInt = G.BigInt;
      var parseInt = G.parseInt;
      var parseFloat = G.parseFloat;
      var isNaN = G.isNaN;
      var isFinite = G.isFinite;
      var encodeURIComponent = G.encodeURIComponent;
      var decodeURIComponent = G.decodeURIComponent;
      var encodeURI = G.encodeURI;
      var decodeURI = G.decodeURI;
      var Uint8Array = G.Uint8Array;
      var Int8Array = G.Int8Array;
      var Uint16Array = G.Uint16Array;
      var Int16Array = G.Int16Array;
      var Uint32Array = G.Uint32Array;
      var Int32Array = G.Int32Array;
      var Float32Array = G.Float32Array;
      var Float64Array = G.Float64Array;
      var ArrayBuffer = G.ArrayBuffer;
      var DataView = G.DataView;
      var TextEncoder = G.TextEncoder;
      var TextDecoder = G.TextDecoder;
      var btoa = G.btoa;
      var atob = G.atob;
      var globalThis = G;
      var self = G;
      var window = G;
      var __helpers = G.__helpers;
      var Buffer = G.Buffer;
      var location = G.location;
      var WebSocket = G.WebSocket;
      var crypto = G.crypto;

      ${code}

      // Write back skill exports to G
      G.__skill = (typeof __skill !== 'undefined') ? __skill : ((typeof globalThis !== 'undefined' && globalThis.__skill) ? globalThis.__skill : G.__skill);
      if (typeof init !== 'undefined') G.init = init;
      if (typeof start !== 'undefined') G.start = start;
      if (typeof stop !== 'undefined') G.stop = stop;
      if (typeof onCronTrigger !== 'undefined') G.onCronTrigger = onCronTrigger;
      if (typeof onSetupStart !== 'undefined') G.onSetupStart = onSetupStart;
      if (typeof onSetupSubmit !== 'undefined') G.onSetupSubmit = onSetupSubmit;
      if (typeof onSetupCancel !== 'undefined') G.onSetupCancel = onSetupCancel;
      if (typeof onSessionStart !== 'undefined') G.onSessionStart = onSessionStart;
      if (typeof onSessionEnd !== 'undefined') G.onSessionEnd = onSessionEnd;
      if (typeof onListOptions !== 'undefined') G.onListOptions = onListOptions;
      if (typeof onSetOption !== 'undefined') G.onSetOption = onSetOption;
    `);
    fn(G);
  };

  // Run skill code
  try {
    runInContext(skillCode);
    console.log(`${colors.green}✓${colors.reset} Skill code loaded`);
  } catch (e) {
    console.error(`${colors.red}Error evaluating skill code: ${e}${colors.reset}`);
    process.exit(1);
  }

  // Extract skill from __skill.default (bundled skills expose this way)
  interface SkillExport {
    tools?: Array<{ name: string; description: string; execute: (args: Record<string, unknown>) => string }>;
    init?: () => void;
    start?: () => void;
    stop?: () => void;
    onCronTrigger?: (id: string) => void;
    onSetupStart?: () => unknown;
    onSetupSubmit?: (args: { stepId: string; values: Record<string, unknown> }) => unknown;
    onSessionStart?: (args: { sessionId: string }) => void;
    onSessionEnd?: (args: { sessionId: string }) => void;
    onListOptions?: () => { options: unknown[] };
    onSetOption?: (args: { name: string; value: unknown }) => void;
  }

  const skillExport = G.__skill as { default?: SkillExport } | undefined;
  const skill = skillExport?.default;

  if (skill) {
    if (skill.tools) G.tools = skill.tools;
    if (skill.init && !G.init) G.init = skill.init;
    if (skill.start && !G.start) G.start = skill.start;
    if (skill.stop && !G.stop) G.stop = skill.stop;
    if (skill.onCronTrigger && !G.onCronTrigger) G.onCronTrigger = skill.onCronTrigger;
    if (skill.onSetupStart && !G.onSetupStart) G.onSetupStart = skill.onSetupStart;
    if (skill.onSetupSubmit && !G.onSetupSubmit) G.onSetupSubmit = skill.onSetupSubmit;
    if (skill.onSessionStart && !G.onSessionStart) G.onSessionStart = skill.onSessionStart;
    if (skill.onSessionEnd && !G.onSessionEnd) G.onSessionEnd = skill.onSessionEnd;
    if (skill.onListOptions && !G.onListOptions) G.onListOptions = skill.onListOptions;
    if (skill.onSetOption && !G.onSetOption) G.onSetOption = skill.onSetOption;
  }

  // Report what was found
  const toolCount = G.tools ? (G.tools as unknown[]).length : 0;
  if (toolCount > 0) {
    console.log(`${colors.dim}  Found ${toolCount} tools${colors.reset}`);
  }
  console.log(`${colors.green}✓${colors.reset} Skill exports extracted`);

  // Define helper functions as JavaScript code to inject
  const helperDefinitions = `
// Expose skill functions as local vars for helper code
var tools = G.tools;
var init = G.init;
var start = G.start;
var stop = G.stop;
var onCronTrigger = G.onCronTrigger;
var onSetupStart = G.onSetupStart;
var onSetupSubmit = G.onSetupSubmit;
var onSetupCancel = G.onSetupCancel;
var onSessionStart = G.onSessionStart;
var onSessionEnd = G.onSessionEnd;
var onListOptions = G.onListOptions;
var onSetOption = G.onSetOption;

function callTool(name, args) {
  args = args || {};
  var validTools = tools.filter(function(t) { return t && t.name; });
  var tool = validTools.find(function(t) { return t.name === name; });
  if (!tool) {
    throw new Error('Tool "' + name + '" not found. Available: ' + validTools.map(function(t) { return t.name; }).join(', '));
  }
  var result = tool.execute(args);
  try {
    return JSON.parse(result);
  } catch (e) {
    return result;
  }
}

function triggerCron(scheduleId) {
  if (typeof onCronTrigger === 'function') {
    onCronTrigger(scheduleId);
  } else {
    console.warn('onCronTrigger not defined');
  }
}

function triggerSetupStart() {
  if (typeof onSetupStart === 'function') return onSetupStart();
  console.warn('onSetupStart not defined');
  return null;
}

function triggerSetupSubmit(stepId, values) {
  if (typeof onSetupSubmit === 'function') return onSetupSubmit({ stepId: stepId, values: values });
  console.warn('onSetupSubmit not defined');
  return null;
}

function triggerSessionStart(sessionId) {
  if (typeof onSessionStart === 'function') onSessionStart({ sessionId: sessionId });
}

function triggerSessionEnd(sessionId) {
  if (typeof onSessionEnd === 'function') onSessionEnd({ sessionId: sessionId });
}

function triggerTimer(timerId) {
  var mockState = __helpers.getMockState();
  var timer = mockState.timers.get(timerId);
  if (timer) {
    timer.callback();
    if (!timer.isInterval) mockState.timers.delete(timerId);
  } else {
    console.warn('Timer ' + timerId + ' not found');
  }
}

function listTools() {
  return tools.filter(function(t) { return t && t.name; }).map(function(t) { return t.name; });
}

function listTimers() {
  var state = __helpers.getMockState();
  var result = [];
  state.timers.forEach(function(timer, id) {
    result.push({ id: id, delay: timer.delay, isInterval: timer.isInterval });
  });
  return result;
}

function __mockFetch(url, response) {
  __helpers.mockFetchResponse(url, response.status, response.body, response.headers);
}

function __mockFetchError(url, message) {
  __helpers.mockFetchError(url, message);
}

function __getMockState() {
  return __helpers.getMockState();
}

function __resetMockState() {
  __helpers.resetMockState();
}

function __setEnv(key, value) {
  __helpers.setEnv(key, value);
}

function __setPlatformOs(os) {
  __helpers.setPlatformOs(os);
}
`;

  // Call init() if available
  if (typeof G.init === 'function') {
    console.log(`${colors.dim}Calling init()...${colors.reset}`);
    try {
      (G.init as () => void)();
      console.log(`${colors.green}✓${colors.reset} init() completed`);
    } catch (e) {
      console.error(`${colors.red}init() error: ${e}${colors.reset}`);
    }
  }

  // Call start() if available
  if (typeof G.start === 'function') {
    console.log(`${colors.dim}Calling start()...${colors.reset}`);
    try {
      (G.start as () => void)();
      console.log(`${colors.green}✓${colors.reset} start() completed`);
    } catch (e) {
      console.error(`${colors.red}start() error: ${e}${colors.reset}`);
    }
  }

  // Load and execute the test script
  console.log(`\n${colors.yellow}═══════════════════════════════════════════════════════════════${colors.reset}`);
  console.log(`${colors.yellow}                    Running Test Script                        ${colors.reset}`);
  console.log(`${colors.yellow}═══════════════════════════════════════════════════════════════${colors.reset}`);
  console.log(`${colors.dim}Script: ${resolvedScriptPath}${colors.reset}\n`);

  const scriptCode = readFileSync(resolvedScriptPath, 'utf-8');
  const fullScript = helperDefinitions + '\n' + scriptCode;

  try {
    runInContext(fullScript);
    console.log(`\n${colors.green}═══════════════════════════════════════════════════════════════${colors.reset}`);
    console.log(`${colors.green}                    Script Completed                           ${colors.reset}`);
    console.log(`${colors.green}═══════════════════════════════════════════════════════════════${colors.reset}`);
  } catch (e) {
    console.error(`\n${colors.red}═══════════════════════════════════════════════════════════════${colors.reset}`);
    console.error(`${colors.red}                    Script Error                               ${colors.reset}`);
    console.error(`${colors.red}═══════════════════════════════════════════════════════════════${colors.reset}`);
    console.error(`${colors.red}${e}${colors.reset}`);
    process.exit(1);
  }

  // Wait for async operations if --wait was specified
  if (waitMs > 0) {
    console.log(`\n${colors.dim}Waiting ${waitMs}ms for async operations...${colors.reset}`);
    await new Promise((resolve) => setTimeout(resolve, waitMs));
    console.log(`${colors.green}✓${colors.reset} Wait completed`);
  }

  // Call stop() if available
  if (typeof G.stop === 'function') {
    console.log(`\n${colors.dim}Calling stop()...${colors.reset}`);
    try {
      (G.stop as () => void)();
      console.log(`${colors.green}✓${colors.reset} stop() completed`);
    } catch (e) {
      console.error(`${colors.red}stop() error: ${e}${colors.reset}`);
    }
  }
}

main();
